# The topology this project follows

Observed from existing authenticated, read-only Proxmox API/SSH on October 20,
2026 around 23:57 Asia/Bangkok. See evidence/topology-2026-10-20.json. IPs come from
the current repository inventory; CPU, RAM, active disks and owners were refreshed live.

| VM | ID | Host | IP | vCPU | RAM MiB | OS disk GiB | OS storage |
|---|---:|---|---|---:|---:|---:|---|
| tombstone | 100 | endgame | 192.168.63.20 | 2 | 2560 | 64 | local-ssd |
| whyachi | 101 | endgame | 192.168.63.21 | 2 | 2048 | 64 | local-ssd |
| biteforce | 111 | deepsix | 192.168.63.67 | 2 | 2560 | 32.5 | local-zfs |
| huge | 104 | deepsix | 192.168.63.23 | 3 | 4712 | 64 | local-zfs |
| minotaur | 106 | endgame | 192.168.63.25 | 3 | 4712 | 64 | local-zfs |
| valkyrie | 109 | deepsix | 192.168.63.22 | 2 | 2048 | 64 | local-ssd |
| hydra | 108 | endgame | 192.168.63.113 | 1 | 1024 | 16 | local-zfs |

All use one CPU socket, cpu=host, a VirtIO NIC on vmbr0, virtio-scsi-single,
SeaBIOS by absence of a firmware override, and guest-agent communication. Existing
onboot=1 is preserved. The six ordinary VMs sum to 18,640 MiB RAM; Hydra adds 1,024
MiB (check host headroom and filesystem overhead independently).

Endgame: 10,344 MiB VM RAM; Deep Six: 9,320 MiB VM RAM, excluding the Tailscale LXC
and future template test machines. Those totals are allocation, not peak usage.

Storage configuration observed:

* local-zfs: ZFS rpool/data, images/rootdir on both nodes.
* local-ssd: ZFS ssdpool, images/rootdir on both nodes.
* local: directory /var/lib/vz, currently no snippets content enabled.
* nas-backup: existing NFS backup storage, not a bootstrap dependency for this project.

Same-named local storage is physically node-local, not shared. Both template sources
are prepared locally so the fleet does not depend on cross-node cloning/migration.

## Exact matches and deliberate rebuild differences

* Names/IDs, CPU/RAM, NIC identities and current host placement are copied.
* Ubuntu source OS is standardized to Minimal 24.04 LTS at your request; this is not
  a byte-for-byte reproduction of the mixed installed OS versions.
* You approved uniform K3s disk provisioning. All FIVE K3s guests get 32-GiB OS disks.
  Control planes use local-zfs, workers use local-ssd. Valkyrie retains 64 GiB on
  local-ssd. Hydra retains 16 GiB on local-zfs and separate physical USB data.
* These are NEW-build sizes, not supported instructions to shrink your live 64-GiB
  disks. The evidence table above deliberately keeps the original observed values.
* Each Ubuntu source template is 8 GiB; Terraform expands its clones to their role size.
* Cloud-init metadata is newly added to all Ubuntu VMs, so every fresh guest can
  acquire identity/access automatically. Cloud-init media uses its role's disk pool.
* New templates are 9100/endgame and 9101/deepsix. Existing template 105 is not
  modified or assumed to be the new minimal/prepared image. The NAS template is 9102.
* Serial console is enabled on the new Ubuntu fleet for recovery, even where not
  present in the original guest. VM protection and prevent_destroy are enabled.
* VM tags describe intended roles; they do not install or enable K3s. Valkyrie is a
  general guest, not an automatically rejoined control plane.
* The observed Hydra attachment is usb1 host=2-10. The Terraform provider creates
  its first USB block as usb0 using a named mapping to that same intended device.
  Slot label changes; no data is formatted. Mapping must be verified for each target.
* Hydra's existing disk contains OMV 8.5.11-1. Prepare an OMV 8 / Debian 13 source;
  matching the exact package version requires retaining that version's installer/
  packages. A newer OMV 8 build is a documented version difference, not an exact clone.

The .1 gateway, /24 prefix and .102 DNS match the recorded LAN configuration; verify
availability in the replacement environment. .69 is reserved for the future K3s API
VIP; this project does not assign it to a VM. Proxmox hosts remain .10 and .11.

## Deliberately outside this VM fleet

* tailscale-router1, LXC 103 on deepsix: discovered and recorded, but not recreated
  because this request covers VMs. Provide direct LAN access while bootstrapping.
* Pi/QDevice and DNS .102, router .1: independent prerequisites, not guest VMs here.
* Physical Proxmox installation, cluster formation, pools, quorum device, NAS files,
  K3s state, HA/replication/backup policies: not silently inferred or recreated.

A two-host layout with two control planes on Endgame reproduces your observed
failure domains; it is not a claim that the cluster survives loss of either host.

## Approved new-build storage policy and budget

| Role | Root size | Root/cloud-init pool |
|---|---:|---|
| control-plane (3 guests) | 32 GiB | local-zfs |
| worker (2 guests) | 32 GiB | local-ssd |
| general (Valkyrie) | 64 GiB | local-ssd |
| NAS (Hydra) | 16 GiB | local-zfs |

The Deep Six local-ssd status query returned total=115494354944 bytes (~107.6 GiB).
A 64-GiB worker plus 64-GiB Valkyrie would exceed that capacity. The selected 32+64
GiB instead allocates 96 GiB of guest OS capacity there, leaving only modest nominal
headroom. Snapshots, metadata, existing contents and future growth still matter.
This is not a reservation or a guarantee that workloads fit.

Budget by node/pool, excluding templates and Proxmox's own usage:
Endgame local-zfs=80 GiB (two controls + Hydra), local-ssd=32 GiB (Minotaur).
Deep Six local-zfs=32 GiB (Biteforce), local-ssd=96 GiB (Huge + Valkyrie).
Prepared templates add 8-GiB virtual images on each local-zfs and a 16-GiB NAS source
on Endgame. Verify usable physical capacity plus a deliberate snapshot/growth margin.
Worker OS disks are not a promised Longhorn/data-storage allocation. Size workload
data separately before deploying stateful applications.
