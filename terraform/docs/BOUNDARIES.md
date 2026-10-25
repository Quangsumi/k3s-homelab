# What this deployment owns

Terraform owns the six Ubuntu VM hardware definitions, their cloud-init snippet
files and the Hydra VM definition with its USB mapping attachment. The prepared
source templates are explicit external inputs, not automatically deleted resources.

Cloud-init creates VM-named key-only user accounts with passwordless sudo and
MAC-matched ens18 static networking. The prepared Ubuntu OS contains the guest
agent and Python, so later configuration can use SSH immediately after readiness
checks. No cloud-init package installation is left racing Ansible on first boot.
No private key, root password, API token or Kubernetes token is put in user-data.

## Same topology does not mean restored applications

The project recreates machine shape and initial OS access, with approved uniform
K3s disk policies. It does not reproduce old etcd identities, cluster membership,
application configuration, PostgreSQL data, NAS files or old service secrets.
HA/replication schedules, backup jobs, physical network workarounds, SSD tuning,
Proxmox host installation and pools are separate preparation/operations concerns.
The external router, Pi/QDevice/DNS and existing Tailscale LXC remain prerequisites.

## Disk and network ownership

An 8-GiB template is full-cloned, then each Ubuntu disk grows to its role size.
Never use this fresh-build project as instructions for shrinking or migrating an
existing guest. Control planes use local-zfs; workers use local-ssd. These names
must map to the intended separate physical pools on the target; they do not prove
performance, durability or enough capacity. Allow for snapshots, host OS and future
workload data. Thin provisioning does not create physical storage capacity.

Hydra is pinned to Endgame because the USB disk is physically there. HA migration
cannot make that disk appear on Deep Six. USB passthrough is not data replication.
Terraform can attach a reviewed mapping but cannot recover the contents of a lost
USB disk. Do not make NAS data disposable just because its OS VM is reproducible.

Cloud-init provides INITIAL Ubuntu network configuration. Later Ansible network
management must explicitly take ownership; do not run both as conflicting authorities.
OMV owns Hydra's guest network, using a dedicated source prepared for this single
static identity. DNS records are configured through the actual DNS server, not by
writing a resolver address on a guest.

## Adoption, destruction and consistency

Do not import the live guests into these fresh Ubuntu clone resources casually.
Import needs a separate audited migration/adoption design that matches their real
OS, disks and unmanaged settings without planning replacements. ID/name similarity
is not proof that an existing VM is safe to manage with a new resource definition.

prevent_destroy, protection and reboot_after_update=false reduce accidental
replacement/downtime, but removing configuration/state or changing protection policy
can bypass guardrails. Keep real backups and recovery instructions outside the fleet.
An apply is not a transaction: it can leave some snippets/clones created after a
failure. Inspect partial results and state before retrying, rather than deleting VMs.

The base Ubuntu artifact is pinned/checksummed. Offline apt installation is not a
package-repository snapshot; retain the final built image/hash and OMV source/ISO
for repeatability. Pin and review provider lock files. A new cluster gets NEW state.

## Sources used for this implementation

* [Pinned VM resource schema](https://github.com/bpg/terraform-provider-proxmox/blob/v0.117.0/docs/resources/virtual_environment_vm.md)
* [Pinned snippet upload resource](https://github.com/bpg/terraform-provider-proxmox/blob/v0.117.0/docs/resources/virtual_environment_file.md)
* [Terraform state](https://developer.hashicorp.com/terraform/language/state)
* [Cloud-init CLI and image cleaning](https://docs.cloud-init.io/en/latest/reference/cli.html)
* [OMV installation](https://docs.openmediavault.org/en/stable/installation/index.html)
