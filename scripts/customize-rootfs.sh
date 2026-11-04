#!/usr/bin/env bash
# Invoked INSIDE an image chroot/container, never on a workstation.
set -euo pipefail
[[ -e /run/linux-desktop-image-build ]] || { echo 'Missing image build marker' >&2; exit 1; }
[[ $(id -u) == 0 ]] || exit 1
# shellcheck source=/dev/null
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 ]] || { echo 'Requires Ubuntu 26.04' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
arch=$(dpkg --print-architecture)
[[ "$arch" == amd64 || "$arch" == arm64 ]] || exit 1
# /opt/linux-desktop is copied by the external image builder.
cd /opt/linux-desktop
apt-get update
mapfile -t packages < <(cat config/common.packages "config/$arch.packages" | sed '/^[[:space:]]*#/d;/^[[:space:]]*$/d' | grep -v '^linux-desktop$')
apt-get install -y "${packages[@]}"
python3 scripts/build-deb.py
apt-get install -y ./build/*.deb
glib-compile-schemas /usr/share/glib-2.0/schemas
# Prevent reporting and disable autologin inherited from a live session.
systemctl disable apport.service whoopsie.service 2>/dev/null || true
apt-get clean
rm -f /var/lib/dbus/machine-id
truncate -s 0 /etc/machine-id
