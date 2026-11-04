#!/usr/bin/env bash
# Customize an upstream disk image in an isolated libguestfs appliance.
set -euo pipefail
[[ $# == 4 ]] || { echo 'Usage: build-image.sh pi5|arm64-uefi INPUT SHA256 OUTPUT.qcow2' >&2; exit 2; }
target=$1; input=$(realpath "$2"); expected=$3; output=$(realpath -m "$4")
[[ "$target" == pi5 || "$target" == arm64-uefi ]] || { echo 'Disk-image builder supports pi5 and arm64-uefi only' >&2; exit 2; }
[[ "$expected" =~ ^[a-f0-9]{64}$ ]] || exit 2
[[ ! -e "$output" ]] || { echo 'Refusing to overwrite an output' >&2; exit 2; }
[[ $(uname -m) == aarch64 ]] || { echo 'Use a native ARM64 runner' >&2; exit 2; }
for cmd in virt-customize virt-inspector virt-resize qemu-img sha256sum; do command -v "$cmd" >/dev/null; done
actual=$(sha256sum "$input"); [[ "${actual%% *}" == "$expected" ]] || { echo 'Input checksum mismatch' >&2; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$(dirname "$output")"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
virt-inspector -a "$input" > "$work/inspection.xml"
rootdev=$(python3 - "$work/inspection.xml" <<'PYXML'
import sys
import xml.etree.ElementTree as E
systems=E.parse(sys.argv[1]).findall('./operatingsystem')
if len(systems)!=1: raise SystemExit('Expected exactly one operating system')
os=systems[0]
if os.findtext('distro')!='ubuntu' or os.findtext('major_version')!='26':
    raise SystemExit('Expected Ubuntu 26.04 image')
print(os.findtext('root'))
PYXML
)
[[ "$rootdev" =~ ^/dev/[a-zA-Z0-9/]+$ ]] || exit 2
size=$(qemu-img info --output=json "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin)["virtual-size"]+16*1024**3)')
qemu-img create -f qcow2 "$output" "$size"
virt-resize --expand "$rootdev" "$input" "$output"
git -C "$root" archive --format=tar HEAD > "$work/source.tar"
virt-customize --format qcow2 -a "$output" --memsize 4096 --smp 2 \
  --mkdir /opt/linux-desktop --upload "$work/source.tar:/opt/source.tar" \
  --run-command 'tar -xf /opt/source.tar -C /opt/linux-desktop; rm /opt/source.tar' \
  --run-command 'mkdir -p /run; touch /run/linux-desktop-image-build' \
  --run-command 'bash /opt/linux-desktop/scripts/customize-rootfs.sh' \
  --run-command 'rm -rf /opt/linux-desktop /run/linux-desktop-image-build'
qemu-img check "$output"
sha256sum "$output" > "$output.sha256"
echo 'Image built. Not release-certified; run the target hardware acceptance suite.'
