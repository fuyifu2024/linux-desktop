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
  local failed=0
  for point in run sys proc dev; do
    if mountpoint -q "$work/fs/$point"; then
      if ! umount -R "$work/fs/$point"; then failed=1; fi
    fi
  done
  # Never recurse into a remaining bind mount: it may expose the host filesystem.
  if [[ $failed == 0 ]]; then
    rm -rf "$work"
  else
    echo "Unmount failed; preserving work directory: $work" >&2
  fi
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
cp -a --no-dereference "$work/fs/etc/resolv.conf" "$work/resolv.conf.original"
cp --remove-destination /etc/resolv.conf "$work/fs/etc/resolv.conf"
chroot "$work/fs" bash /opt/linux-desktop/scripts/customize-rootfs.sh
# dpkg-query expands these placeholders, not the build shell.
# shellcheck disable=SC2016
chroot "$work/fs" dpkg-query -W -f='${Package} ${Version}\n' > "$work/iso/casper/filesystem.manifest"
for point in run sys proc dev; do umount -R "$work/fs/$point"; done
rm -rf "$work/fs/opt/linux-desktop"
rm -f "$work/fs/etc/resolv.conf"
cp -a --no-dereference "$work/resolv.conf.original" "$work/fs/etc/resolv.conf"
size=$(du -sx --block-size=1 "$work/fs" | cut -f1)
printf '%s\n' "$size" > "$work/iso/casper/filesystem.size"
rm "$work/iso/$squash"
mksquashfs "$work/fs" "$work/iso/$squash" -noappend -comp xz
(cd "$work/iso"; find . -type f ! -name md5sum.txt ! -path './boot/*' -print0 | sort -z | xargs -0 md5sum > "$work/md5sum.txt")
mv "$work/md5sum.txt" "$work/iso/md5sum.txt"
xorriso -indev "$input" -outdev "$output" -boot_image any replay \
  -map "$work/iso/$squash" "/$squash" \
  -map "$work/iso/casper/filesystem.manifest" /casper/filesystem.manifest \
  -map "$work/iso/casper/filesystem.size" /casper/filesystem.size \
  -map "$work/iso/md5sum.txt" /md5sum.txt
sha256sum "$output" > "$output.sha256"
