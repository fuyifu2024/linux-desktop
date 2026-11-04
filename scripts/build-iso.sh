#!/usr/bin/env bash
# Rebuild an Ubuntu desktop ISO, preserving its upstream boot configuration.
set -euo pipefail
[[ $# == 4 ]] || { echo 'Usage: build-iso.sh INPUT.iso SHA256 ROOT_SQUASHFS OUTPUT.iso' >&2; exit 2; }
input=$(realpath "$1"); expected=$2; squash=$3; output=$(realpath -m "$4")
[[ $EUID == 0 && $(uname -m) == x86_64 ]] || { echo 'Use an isolated root-capable x86_64 builder' >&2; exit 2; }
[[ "$expected" =~ ^[a-f0-9]{64}$ && "$squash" =~ ^casper/[a-zA-Z0-9._-]+\.squashfs$ ]] || exit 2
[[ ! -e "$output" ]] || exit 2
for cmd in xorriso unsquashfs mksquashfs chroot; do command -v "$cmd" >/dev/null; done
actual=$(sha256sum "$input"); [[ "${actual%% *}" == "$expected" ]] || { echo 'Checksum mismatch' >&2; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
cleanup() {
  for point in run sys proc dev; do mountpoint -q "$work/fs/$point" && umount -R "$work/fs/$point" || true; done
  rm -rf "$work"
}
trap cleanup EXIT
xorriso -osirrox on -indev "$input" -extract / "$work/iso"
# Layered Ubuntu media needs installation-source metadata integration. Do not
# produce an ISO that boots but silently installs the uncustomized upstream OS.
mapfile -t layers < <(find "$work/iso/casper" -name '*.squashfs')
[[ ${#layers[@]} == 1 ]] || { echo 'Layered ISO detected: installation-source integration is not yet validated; build refused.' >&2; exit 1; }
unsquashfs -d "$work/fs" "$work/iso/$squash"
mkdir -p "$work/fs/opt/linux-desktop"
git -C "$root" archive HEAD | tar -x -C "$work/fs/opt/linux-desktop"
for point in dev proc sys run; do mount --rbind "/$point" "$work/fs/$point"; mount --make-rslave "$work/fs/$point"; done
# Do not share host /run: replace it with a private tmpfs before the marker.
umount -R "$work/fs/run"
mount -t tmpfs tmpfs "$work/fs/run"
touch "$work/fs/run/linux-desktop-image-build"
chroot "$work/fs" bash /opt/linux-desktop/scripts/customize-rootfs.sh
chroot "$work/fs" dpkg-query -W -f='${Package} ${Version}\n' > "$work/iso/casper/filesystem.manifest"
for point in run sys proc dev; do umount -R "$work/fs/$point"; done
rm -rf "$work/fs/opt/linux-desktop"
size=$(du -sx --block-size=1 "$work/fs" | cut -f1)
printf '%s\n' "$size" > "$work/iso/casper/filesystem.size"
rm "$work/iso/$squash"
mksquashfs "$work/fs" "$work/iso/$squash" -noappend -comp xz
(cd "$work/iso"; find . -type f ! -name md5sum.txt ! -path './boot/*' -print0 | sort -z | xargs -0 md5sum > md5sum.txt)
xorriso -indev "$input" -outdev "$output" -boot_image any replay \
  -map "$work/iso/$squash" "/$squash" \
  -map "$work/iso/casper/filesystem.manifest" /casper/filesystem.manifest \
  -map "$work/iso/casper/filesystem.size" /casper/filesystem.size \
  -map "$work/iso/md5sum.txt" /md5sum.txt
sha256sum "$output" > "$output.sha256"
