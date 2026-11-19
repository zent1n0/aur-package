#!/usr/bin/env bash
set -euo pipefail

package="$1"
version="$2"
build="$3"
dry_run="$4"
work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT

mirror="${AUR_MIRROR:-https://github.com/archlinux/aur.git}"
git clone --quiet --depth=1 --single-branch --branch "$package" "$mirror" "$work_dir/aur"
cd "$work_dir/aur"

base="$(git rev-parse HEAD)"
current="$(makepkg --printsrcinfo | awk '$1 == "pkgver" && $2 == "=" { print $3 }')"
[[ -n "$current" ]] || { echo 'Could not determine the AUR pkgver.' >&2; exit 1; }
comparison="$(vercmp "$version" "$current")"
printf '%s: AUR %s, upstream %s\n' "$package" "$current" "$version" >&2

if [[ "$comparison" != 1 ]]; then
  if [[ "$build" == true && "$dry_run" == true ]]; then
    makepkg --syncdeps --noconfirm --cleanbuild >&2
  fi
  printf 'version=%s\n' "$version"
  exit 0
fi

sed -i -e "s/^pkgver=.*/pkgver=$version/" -e 's/^pkgrel=.*/pkgrel=1/' PKGBUILD
metadata="$(makepkg --printsrcinfo)"
grep -Eq "^[[:space:]]*pkgver = " <<< "$metadata"
[[ "$(awk '$1 == "pkgver" && $2 == "=" { print $3 }' <<< "$metadata")" == "$version" &&
   "$(awk '$1 == "pkgrel" && $2 == "=" { print $3 }' <<< "$metadata")" == 1 ]] ||
  { echo 'PKGBUILD requires a custom version bump.' >&2; exit 1; }

updpkgsums >&2
makepkg --printsrcinfo > .SRCINFO
patch="$(git diff --binary HEAD -- PKGBUILD .SRCINFO | base64 -w0)"
[[ -n "$patch" ]]

if [[ "$build" == true ]]; then
  makepkg --syncdeps --noconfirm --cleanbuild >&2
fi

printf 'version=%s\nbase=%s\npatch=%s\n' "$version" "$base" "$patch"
