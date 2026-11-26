# AUR Package Updates

This repository automatically updates selected AUR packages I maintain. GitHub Actions checks upstream releases with `nvchecker` at 00:00, 06:00, 12:00, and 18:00 UTC.

| Package | Description | Upstream | Build check |
| --- | --- | --- | --- |
| [`osu-lazer`](https://aur.archlinux.org/packages/osu-lazer) | Source build of osu!lazer, the open-source rhythm game | [`ppy/osu`](https://github.com/ppy/osu/releases), stable lazer releases | Enabled |
| [`python-certbot-pkcs12`](https://aur.archlinux.org/packages/python-certbot-pkcs12) | PKCS#12 installer plugin for Certbot | [`nasa-gcn/certbot-pkcs12`](https://github.com/nasa-gcn/certbot-pkcs12/releases) | Enabled |

## How it works

For each package, CI reads the current AUR packaging files directly from the AUR over unauthenticated HTTPS. When upstream is newer, it bumps `pkgver`, resets `pkgrel`, recalculates checksums, and regenerates `.SRCINFO`. If enabled, `makepkg` builds and packages the update inside an x86_64 Arch Linux container. Build artifacts are discarded.

A separate job applies the tested changes and pushes them to AUR over SSH. It stops if the live AUR repository has moved. GitHub runs schedules from the default branch and can disable schedules in public repositories after 60 days of inactivity.

## Setup

Register the CI public key with your AUR account and add its private key as the GitHub Actions repository secret `AUR_SSH_KEY`. The key authenticates as your AUR account. The build job runs without the SSH key.

Use **Actions → Update AUR packages → Run workflow** for a manual run. Specify a pkgbase to run a single package. Dry-run mode is enabled by default for manual runs and can test the current package when no update is pending.

## Adding packages

Create `packages/<pkgbase>/.nvchecker.toml` and configure the upstream source to return the value used by `pkgver`. Copy the `[__config__]` section from the existing package. Add `update.toml` with `build = true` to require a successful package build before publication. Without that setting, CI prepares the update and publishes it without a build.

The updater supports standard `pkgver=` and `pkgrel=` assignments. Packages with custom version logic or dependencies outside official Arch repositories may require additional handling.
