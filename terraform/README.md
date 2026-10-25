# Rebuild this Proxmox VM fleet

Start with [PREPARE.md](docs/PREPARE.md), then follow [DEPLOY.md](docs/DEPLOY.md).
This project prepares fresh, key-accessible operating systems for later Ansible work.
It does not install Kubernetes, restore databases/files, or adopt existing VMs.

The target is your **two-node topology**: endgame and deepsix, vmbr0,
local-zfs/rpool and local-ssd/ssdpool. There is no invented third node, auth VM or
PostgreSQL VM. Six ordinary guests use Ubuntu Server Minimal 24.04 LTS as requested.
Hydra uses a dedicated OpenMediaVault 8 template and its physical USB data device.

## What was actually observed?

Read-only Proxmox metadata was sampled on October 20, 2026 at 16:57 UTC
(23:57 Bangkok). [TOPOLOGY.md](docs/TOPOLOGY.md) records the hardware and distinctions
between observed facts, rebuild choices and prerequisites. Hydra's installed
OpenMediaVault package was read as 8.5.11-1. No VM configuration was changed.

These IDs, addresses and MACs are **already occupied on your live cluster**.
Use the supplied environment only on an empty, network-isolated replacement cluster.
This is not a way to run a second copy next to the existing fleet. The default
fresh_target_confirmed=false guard blocks a VM plan until deliberately acknowledged.
Preflight also rejects occupied IDs. Never delete existing VMs just to clear that check.

## Project map

| Location | Purpose |
|---|---|
| scripts/build-ubuntu-image.sh | Download/check the pinned minimal image; prepare it offline |
| scripts/create-ubuntu-template.sh | Import that prepared image into an unused template on each node |
| scripts/preflight.py | Read-only empty-target/template/storage checks |
| scripts/capture-topology.py | Reusable credential-filtered read-only hardware snapshot |
| environments/current/compute.tfvars | Six observed Ubuntu VM definitions |
| environments/current/nas.tfvars | Hydra template/mapping inputs |
| stacks/compute/ | Independently applied Ubuntu fleet |
| stacks/nas/ | Independently applied Hydra OS and USB mapping attachment |
| modules/linux-vm/ | Reusable full-clone VM definition |
| evidence/ | Source hardware/checksum records without passwords/private keys |

The two stack directories have separate state. Keep them separate. The pinned
provider is bpg/proxmox 0.117.0; both dependency lock files are included.

## What a successful deployment gives you

* The recorded names, IDs, host placement, CPU/RAM, role-based OS disk sizes/storages (the approved uniform rebuild policy),
  MAC addresses, bridge and firewall flags.
* Ubuntu hostname/IP/DNS, a VM-named account, your existing public key, passwordless
  sudo, Python 3 and a running guest agent. Guest/password SSH is disabled initially.
* A cloned Hydra OMV OS with the root key/static network configured during its
  dedicated template preparation; a reviewed USB resource mapping attached.
* Terraform output describing the fleet, ready for a later configuration tool.

It does not copy live OS disks, secrets, Kubernetes/etcd identities, NFS configuration,
NAS data, HA/replication schedules or storage pools. Those are separate concerns.
See [BOUNDARIES.md](docs/BOUNDARIES.md) before changing an existing deployment.

## Local validation

[VALIDATION.md](VALIDATION.md) records real terraform validate and mocked plan tests.
No real plan/apply, template import, image customization or cloud-init boot test
has been performed by this agent. Treat the preparation boot checks as required.
