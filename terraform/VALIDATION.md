# Validation — October 21, 2026

## Passed locally

* Terraform CLI 1.13.5, pinned bpg/proxmox provider 0.117.0; dependency locks generated.
* terraform fmt and terraform validate for both compute and NAS stacks.
* Mock-provider compute plan: six recorded names/IDs, measured CPU/RAM values,
  approved uniform disk profiles, key-only cloud-init accounts and ens18 network data.
* Mock-provider role-storage plan: control-plane roots on local-zfs, workers on
  local-ssd, all five K3s roots 32 GiB.
* Mock-provider NAS plan: Hydra ID 108/Endgame, 1024 MiB, 16-GiB OS disk and named USB
  mapping; no invented second virtual data disk.
* bash -n in WSL for both preparation shell scripts after Linux newline normalization.
* Pinned Ubuntu Minimal build 20261017 checksum matched the dated official
  SHA256SUMS manifest. The image itself has not been downloaded or boot-tested here.

Mock plans use mock_provider and cannot create or contact Proxmox. Three runs passed.
Local provider startup required an unsandboxed IPC listener; no real API plan was run.

## Read-only live evidence collected

* Fleet IDs/names/owners and allowlisted CPU, memory, active disk, NIC and storage
  configuration: October 20, 2026 16:57 UTC / 23:57 Asia/Bangkok.
* Hydra package query via guest agent: openmediavault 8.5.11-1.
* Deep Six local-ssd total capacity: 115494354944 bytes (~107.6 GiB), informing the
  later approved uniform 32-GiB K3s root policy. Existing disk sizes are retained in
  the evidence snapshot; Terraform rebuild policy is intentionally separate.

No live cluster configuration, VM power, guest configuration, disks, keys, credentials
or data were changed. The observed current cluster remains occupied, not a deployment target.

## Still required before deployment

* Actually build/customize the Ubuntu image and retain its final hash/artifact.
* Create and boot-test the fresh templates on an empty isolated target.
* Prepare/verify the dedicated OMV template, root login, network persistence and USB mapping.
* Verify target storage health/capacity, cluster/API/SSH access, CA trust and permissions.
* Preflight on the intended fresh target, real reviewed plans, then explicitly authorized apply.
* Guest-agent, cloud-init, unique identity, filesystem growth and fresh SSH readiness checks.

Mocks/schema checks do not validate image bootability, cloud-init runtime success,
API permissions, storage performance or the NAS data device's identity.

## Re-run without touching the cluster

From the terraform directory on Linux/WSL:

```bash
terraform fmt -check -recursive
terraform -chdir=stacks/compute init -backend=false
terraform -chdir=stacks/compute validate
terraform -chdir=stacks/compute test -var-file=../../environments/current/compute.tfvars
terraform -chdir=stacks/nas init -backend=false
terraform -chdir=stacks/nas validate
terraform -chdir=stacks/nas test -var-file=../../environments/current/nas.tfvars
bash -n scripts/build-ubuntu-image.sh
bash -n scripts/create-ubuntu-template.sh
```
