# Systemd Node Exporter for Linux VMs and Proxmox hosts

This is model 3 host metrics:
central Prometheus scrapes each VM/physical host's Node Exporter directly. It does not install
a Prometheus Agent or collect application business metrics. It manages host services,
including on K3s nodes; it does not change Kubernetes resources.

**Replacing the K3s DaemonSet? Follow [MIGRATION.md](MIGRATION.md) before running.**

The playbook chooses the hosts and calls the shared
[node_exporter role](../../roles/node_exporter/README.md). Lab addresses/verification
live in [inventory settings](../../inventory/group_vars/all/node-exporter.yml).
See the [roles walkthrough](../../ROLES.md)
for how Ansible connects these files. The existing run commands below still apply.

```mermaid
flowchart LR
  A[Ansible] -->|ensure systemd service| V[All Linux VMs and Proxmox hosts: Node Exporter :9100]
  P[Central Prometheus] -->|GET /metrics| V
  V -->|host metric response| P
```

## Selection and existing deployments

| Situation | Behavior |
| --- | --- |
| Inventory `control_planes` or `workers` | Included; same systemd exporter as every other Linux machine |
| Healthy exporter with one recognized running systemd service | Reuse it; no duplicate install |
| Healthy endpoint without a recognized running systemd exporter | Fail; remove the old DaemonSet/container first |
| Recognized exporter service exists but is unhealthy/stopped | Start/enable that service; do not install another or rewrite its config; verify endpoint |
| Neither exporter nor known service exists | Ensure port is free, install Debian/Ubuntu package, bind to machine IP, enable/start |
| Another process owns port before install/start | Fail; operator resolves the existing process |
| Multiple recognized exporter services | Fail; operator chooses which service to keep |
| Already installed by this job | Keep package present, enforce its own listener drop-in, restart only on config changes |

Default inventory selection is **ten machines**: Valkyrie, Tantrum, Hydra, Endgame,
Deep Six, Tombstone, Whyachi, Biteforce, Huge and Minotaur. Hydra/OMV uses
its existing root account; its networking/storage configuration is not changed.
`proxmox_hosts` is included explicitly; existing Proxmox SSH accounts are reused.
The Pi is outside these groups and is not selected. Node Exporter measures the
physical Proxmox OS, not VM inventory/Proxmox API state; an API exporter is a separate future component.
New installs require Debian-family Linux and systemd. Other systems can reuse
an already healthy systemd exporter. Distro package version is used, not an unverified
download of the latest upstream binary.

## Run from `ansible/`

```bash
ansible-playbook playbooks/node-exporter/main.yml --syntax-check
ansible-playbook playbooks/node-exporter/main.yml --list-hosts
ansible-playbook playbooks/node-exporter/main.yml --limit valkyrie --check --diff
ansible-playbook playbooks/node-exporter/main.yml --limit valkyrie
# Physical Proxmox host, same playbook:
ansible-playbook playbooks/node-exporter/main.yml --limit endgame --check --diff
ansible-playbook playbooks/node-exporter/main.yml --limit endgame
```

Use existing SSH/Vault setup (`-e @secrets/vault.yml --ask-vault-pass`) or
`--ask-become-pass` as appropriate. No passwords/keys are added to this job.
If a host uses a different sudo executable, override its existing inventory
setting; e.g. `-e ansible_sudo_exe=/usr/bin/sudo` where required.
One machine is processed at a time; failures stop the rollout. No `--limit` selects
all eligible VMs/Proxmox hosts. Check mode is read-only: it can inspect existing endpoints,
but does not prove a future install/start. New drop-in rendering/start and
post-install reachability checks are skipped where they cannot run in check mode.

## Settings and files

| Setting | Default / use |
| --- | --- |
| `node_exporter_listen_address` | Role default is empty (required input); lab inventory supplies `network_address`, falling back to numeric `ansible_host` for Proxmox hosts |
| `node_exporter_port` | 9100 |
| `node_exporter_verify_from` | Role default `''` disables the extra probe; lab inventory selects `tantrum` for read-only HTTP verification |
| `node_exporter_known_services` | Distro, `node_exporter`, `node-exporter` systemd unit names |
| Package/service/binary | `prometheus-node-exporter`, corresponding service, `/usr/bin/prometheus-node-exporter` |
| `roles/node_exporter/defaults/main.yml` | Reusable defaults; inventory and `-e` can override them |
| `roles/node_exporter/tasks/` | Detect/reuse/install, then verify endpoint and network |
| `20-homelab-listen.conf` template | Managed drop-in under the distro service; only for this job's installation |

No VM power, Proxmox API, quorum, storage or Kubernetes resources are changed.

Package auto-start is suppressed during a new install so a default all-interface
listener is not started before the machine-IP override is applied. An unrelated
existing systemd exporter configuration is not taken over. If it is loopback-only or
uses another port, correct its own settings or select the right port; this job
fails verification rather than silently installing a duplicate.

No firewall rules are changed. Allow the monitoring VM to reach this private
TCP port according to your firewall policy. The endpoint is HTTP and contains
host details; it has no authentication added by this job.

## After running

Local checks require both `node_exporter_build_info` and `node_uname_info`.
The optional delegated probe proves the monitoring VM can retrieve the endpoint,
not that the Prometheus container already scrapes it. Add the reported target to
central Prometheus and verify Targets/queries separately. Re-running a successful
unchanged job should not restart the service.
