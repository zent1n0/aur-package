#!/usr/bin/env bash
set -euo pipefail

: "${AUR_SSH_KEY:?Set the AUR_SSH_KEY repository secret before publishing}"
[[ "$PACKAGE" =~ ^[a-z0-9][a-z0-9+_.-]*$ &&
   "$VERSION" =~ ^[a-zA-Z0-9][a-zA-Z0-9.+_~]*$ &&
   "$BASE" =~ ^[a-f0-9]{40}$ ]] || { echo 'Invalid update metadata.' >&2; exit 1; }

umask 077
work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT
cp scripts/aur-known-hosts "$work_dir/known_hosts"
printf '%s\n' "$AUR_SSH_KEY" > "$work_dir/aur-key"
unset AUR_SSH_KEY
export GIT_SSH_COMMAND="ssh -F /dev/null -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o HostKeyAlgorithms=ssh-ed25519 -o UserKnownHostsFile='$work_dir/known_hosts' -i '$work_dir/aur-key'"

git clone --quiet "ssh://aur@aur.archlinux.org/$PACKAGE.git" "$work_dir/aur"
cd "$work_dir/aur"
[[ "$(git rev-parse HEAD)" == "$BASE" ]] ||
  { echo 'AUR changed since preparation. Retry after the mirror catches up.' >&2; exit 1; }
branch="$(git symbolic-ref --short HEAD)"
printf '%s' "$AUR_PATCH" | base64 --decode |
  git apply --index --include=PKGBUILD --include=.SRCINFO -
git diff --cached --exit-code --quiet -- PKGBUILD &&
  { echo 'Prepared update did not modify PKGBUILD.' >&2; exit 1; }
git -c user.name='Zentino' -c user.email='52699319+zent1n0@users.noreply.github.com' \
  commit -m "Update to $VERSION"
git push origin "HEAD:refs/heads/$branch"
printf 'Published %s %s to the AUR.\n' "$PACKAGE" "$VERSION" >> "$GITHUB_STEP_SUMMARY"
