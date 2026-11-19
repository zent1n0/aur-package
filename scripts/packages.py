import json
import os
from pathlib import Path
import re
import sys
import tomllib


if len(sys.argv) == 1:
    packages = []
    for config in sorted(Path("packages").glob("*/.nvchecker.toml")):
        package = config.parent.name
        if not re.fullmatch(r"[a-z0-9][a-z0-9+_.-]*", package):
            raise SystemExit(f"Invalid pkgbase: {package!r}")
        packages.append(package)
    selected = os.environ.get("SELECTED", "")
    if selected:
        if selected not in packages:
            raise SystemExit(f"Unknown pkgbase: {selected!r}")
        packages = [selected]
    if not packages:
        raise SystemExit("No packages configured.")
    print(f"matrix={json.dumps(packages)}")
else:
    action, package = sys.argv[1:]
    if action == "version":
        path = Path(os.environ["RUNNER_TEMP"]) / "nvchecker-new.json"
        version = json.loads(path.read_text())["data"][package]["version"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_~]*", version):
            raise SystemExit(f"Invalid upstream pkgver for {package}: {version!r}")
        print(version)
    elif action == "build":
        config = Path("packages") / package / "update.toml"
        options = tomllib.loads(config.read_text()) if config.exists() else {}
        build = options.get("build", False)
        if type(build) is not bool:
            raise SystemExit(f"build must be a boolean in {config}")
        print("true" if build else "false")
    else:
        raise SystemExit(f"Unknown action: {action!r}")
