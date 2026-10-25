#!/usr/bin/env bash
# Run on a Linux/WSL image-building workstation, NOT on a live guest.
# Installs nothing on Proxmox. Requires curl, qemu-img and virt-customize locally.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
artifact_dir="$project_dir/artifacts"
mkdir -p "$artifact_dir"
base="$artifact_dir/ubuntu-24.04-minimal-20261017.img"
result="$artifact_dir/ubuntu-24.04-minimal-lab-v1.qcow2"
url=https://cloud-images.ubuntu.com/minimal/releases/noble/release-20261017/ubuntu-24.04-minimal-cloudimg-amd64.img
sha=b3296484e362ba2e713489a5de6225c719d9500962bde25d15f2f21e512c7658
for program in curl qemu-img virt-customize; do command -v "$program" >/dev/null; done
if [[ -e "$result" ]]; then
  printf 'Refusing to replace %s. Version a new image deliberately.\n' "$result" >&2
  exit 1
fi
if [[ ! -f "$base" ]]; then curl --fail --location "$url" --output "$base"; fi
printf '%s  %s\n' "$sha" "$base" | sha256sum --check -
cp --reflink=auto "$base" "$result"
# Packages are installed into the offline image, not into a running fleet VM.
# Use LIBGUESTFS_BACKEND=direct; on WSL without KVM, force_tcg can be slower.
virt-customize -a "$result" \
  --install cloud-init,qemu-guest-agent,python3,openssh-server,sudo \
  --run-command 'systemctl enable ssh.service' \
  --run-command 'cloud-init clean --logs --machine-id' \
  --run-command 'rm -f /etc/ssh/ssh_host_*'
qemu-img check "$result"
sha256sum "$result" > "$result.sha256"
printf 'Image ready: %s\nRecord and reuse this prepared artifact on BOTH nodes.\n' "$result"
