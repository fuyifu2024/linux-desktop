#!/usr/bin/env bash
set -euo pipefail
: "${APT_SIGNING_KEY:?Set the GPG signing key fingerprint}"
: "${APT_OUTPUT:?Set a new output directory}"
[[ ! -e "$APT_OUTPUT" ]] || { echo 'Output already exists' >&2; exit 1; }
mkdir -p "$APT_OUTPUT/pool/main" "$APT_OUTPUT/dists/stable/main/binary-amd64" "$APT_OUTPUT/dists/stable/main/binary-arm64"
cp build/*.deb "$APT_OUTPUT/pool/main/"
cd "$APT_OUTPUT"
for arch in amd64 arm64; do
  apt-ftparchive -a "$arch" packages pool/main > "dists/stable/main/binary-$arch/Packages"
  gzip -n -k "dists/stable/main/binary-$arch/Packages"
done
apt-ftparchive -o APT::FTPArchive::Release::Origin=linux-desktop -o APT::FTPArchive::Release::Suite=stable -o APT::FTPArchive::Release::Codename=stable -o APT::FTPArchive::Release::Architectures='amd64 arm64' -o APT::FTPArchive::Release::Components=main release dists/stable > dists/stable/Release
gpg --batch --yes --local-user "$APT_SIGNING_KEY" --clearsign --output dists/stable/InRelease dists/stable/Release
gpg --batch --yes --local-user "$APT_SIGNING_KEY" --armor --detach-sign --output dists/stable/Release.gpg dists/stable/Release
gpg --armor --export "$APT_SIGNING_KEY" > linux-desktop.asc
