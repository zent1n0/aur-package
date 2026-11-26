import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def options(package):
    config = Path("packages") / package / "update.toml"
    return tomllib.loads(config.read_text()) if config.exists() else {}


def aur_versions(names):
    query = urlencode([("arg[]", name) for name in sorted(set(names.values()))])
    request = Request(
        f"https://aur.archlinux.org/rpc/v5/info?{query}",
        headers={"User-Agent": "zent1n0-aur-package"},
    )
    with urlopen(request, timeout=30) as response:
        info = json.load(response)
    if info.get("type") == "error":
        raise SystemExit(f"AUR RPC: {info.get('error', 'unknown error')}")
    records = {record["Name"]: record for record in info["results"]}
    versions = {}
    for package, name in names.items():
        record = records.get(name)
        if not record or record["PackageBase"] != package:
            print(f"Missing AUR RPC entry for {package} ({name}).", file=sys.stderr)
            continue
        # Arch's full package version is [epoch:]pkgver-pkgrel.
        versions[package] = record["Version"].rpartition("-")[0].split(":")[-1]
        if not versions[package]:
            raise SystemExit(f"Invalid AUR version for {package}: {record['Version']!r}")
    return versions


def upstream_versions(config, current):
    import toml

    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        (work / "old.json").write_text(json.dumps(current))
        keyfile = work / "key.toml"
        keyfile.write_text(toml.dumps({"keys": {"github.com": os.environ.pop("NV_GITHUB_TOKEN")}}))
        config["__config__"] = {"oldver": "old.json", "newver": "new.json"}
        source = work / "nvchecker.toml"
        source.write_text(toml.dumps(config))
        result = subprocess.run(
            ["nvchecker", "--failures", "--tries", "3", "--keyfile", str(keyfile), "-c", str(source)],
            stdout=sys.stderr,
        )
        if result.returncode not in (0, 3):
            result.check_returncode()
        return json.loads((work / "new.json").read_text())["data"]


def check_packages():
    selected = os.environ.get("SELECTED", "")
    configs = {p.parent.name: p for p in sorted(Path("packages").glob("*/.nvchecker.toml"))}
    if selected:
        if selected not in configs:
            raise SystemExit(f"Unknown pkgbase: {selected!r}")
        configs = {selected: configs[selected]}
    if not configs:
        raise SystemExit("No packages configured.")

    sources, names = {}, {}
    for package, path in configs.items():
        name = options(package).get("aur_name", package)
        if not all(re.fullmatch(r"[a-z0-9][a-z0-9+_.-]*", value) for value in (package, name)):
            raise SystemExit(f"Invalid AUR pkgbase or package name for {path}")
        sources[package] = tomllib.loads(path.read_text())[package]
        names[package] = name

    current = aur_versions(names)
    upstream = upstream_versions({p: sources[p] for p in current}, current) if current else {}
    matrix = []
    failed = set(configs) - set(current)
    manual_test = bool(selected) and os.environ.get("DRY_RUN") == "true"
    for package, baseline in current.items():
        version = upstream.get(package, {}).get("version", "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_~]*", version):
            print(f"No valid upstream pkgver for {package}: {version!r}", file=sys.stderr)
            failed.add(package)
            continue
        print(f"{package}: AUR {baseline}, upstream {version}", file=sys.stderr)
        if subprocess.check_output(["vercmp", version, baseline], text=True).strip() == "1":
            matrix.append({"package": package, "version": version})
        elif manual_test and options(package).get("build") is True:
            matrix.append({"package": package, "version": baseline})

    print(f"matrix={json.dumps(matrix)}")
    print(f"incomplete={'true' if failed else 'false'}")


if len(sys.argv) == 1:
    check_packages()
else:
    action, package = sys.argv[1:]
    if action != "build":
        raise SystemExit(f"Unknown action: {action!r}")
    build = options(package).get("build", False)
    if type(build) is not bool:
        raise SystemExit(f"build must be a boolean for {package}")
    print("true" if build else "false")
