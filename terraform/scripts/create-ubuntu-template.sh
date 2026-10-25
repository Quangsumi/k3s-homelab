#!/usr/bin/env bash
# Run explicitly as root on the chosen Proxmox node. Creates ONLY an unused template.
# Usage: bash create-ubuntu-template.sh endgame 9100 /absolute/image.qcow2 SHA256
set -euo pipefail
expected_node=${1:?node name required}
template_id=${2:?unused template ID required}
image=${3:?absolute prepared image path required}
sha=${4:?prepared image SHA256 required}
[[ $(id -u) == 0 ]]
[[ $(hostname -s) == "$expected_node" ]]
[[ "$template_id" =~ ^[0-9]+$ && "$template_id" -ge 9000 ]]
[[ "$sha" =~ ^[0-9a-f]{64}$ && "$image" == /* && -f "$image" ]]
# Cluster-wide ID check: no existing guest can be reused as a template.
pvesh get /cluster/resources --type vm --output-format json | \
  python3 -c 'import json,sys; target=int(sys.argv[1]); assert not any(v["vmid"]==target for v in json.load(sys.stdin)), "ID already exists"' "$template_id"
printf '%s  %s\n' "$sha" "$image" | sha256sum --check -
qm create "$template_id" --name ubuntu-minimal-2404-lab-v1 \
  --memory 2048 --cores 2 --cpu host --bios seabios \
  --scsihw virtio-scsi-single --net0 virtio,bridge=vmbr0 \
  --serial0 socket --agent enabled=1 --onboot 0
qm disk import "$template_id" "$image" local-zfs --format raw
volume=$(qm config "$template_id" | awk -F': ' '$1=="unused0" {print $2}' | cut -d, -f1)
[[ "$volume" == local-zfs:* ]]
qm set "$template_id" --scsi0 "$volume,discard=on,iothread=1"
# Small uniform source; Terraform expands every clone using its role profile.
qm disk resize "$template_id" scsi0 8G
qm set "$template_id" --ide2 local-zfs:cloudinit --boot order=scsi0
qm template "$template_id"
printf 'Created stopped template %s on %s. No existing VM changed.\n' "$template_id" "$expected_node"
