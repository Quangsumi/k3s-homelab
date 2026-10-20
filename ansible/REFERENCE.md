# Ansible for this homelab

This project is prepared, not applied. No VM has been contacted or changed.
Addresses/roles come from the triage skill's October 13, 2026 baseline, not a fresh inventory.
Read [the guided course](LESSONS.md) first, then [networking](NETWORKING.md).

## Scope

* `playbooks/discover.yml`: read guest OS, interfaces, network-manager services and Netplan file names.
* `playbooks/ssh-keys.yml`: add/revoke specified keys for the existing login account; preserve other keys.
* `playbooks/root-access.yml`: optional sudo-based setup of root keys, a Vault-supplied root password hash and root SSH policy; verify a fresh root key login.
* `playbooks/proxmox-agent.yml`: look up a VM by exact Proxmox name, then enable its agent option on the discovered node.
* `playbooks/baseline.yml`: install baseline packages and start the guest agent inside general Linux guests, excluding nas_appliances.
* `playbooks/network.yml`: preserve the current Netplan setup while changing DNS, with automatic backup, validation, apply, reconnect checks and a VM-local rollback timer. Excludes nas_appliances.
* `playbooks/verify.yml`: independently inspect key login, agent service and effective network state.

The network job is automated for the observed Ubuntu/networkd guests. It changes
DNS only, preserving existing IPs, IPv6, routes, interface matching and naming.
It reads current configuration itself and consolidates it only when a DNS change
is needed. A small rollback helper runs on the VM if SSH is lost. See NETWORKING.md.
Hydra's generated Netplan files remain owned by OpenMediaVault. No OS upgrades,
K3s configuration changes, router settings or DNS records are managed here.

## Controller

Use Ubuntu WSL or a Linux management machine with Python 3.11+ and OpenSSH.
Run from this directory so Ansible finds ansible.cfg. On WSL's Windows-mounted
filesystem Ansible may ignore a config in a world-writable directory: explicitly
export ANSIBLE_CONFIG="$PWD/ansible.cfg" as shown in LESSONS.md.
Verify SSH host fingerprints using a trusted console; do not turn checking off.
Password SSH may require `sshpass` depending on the controller's SSH plugin/version.
Targets need SSH and Python 3; bootstrap Python manually through console if absent.

## Configuration

Shared settings live in inventory/group_vars/all/main.yml. Per-host overrides go in
inventory/host_vars/<inventory-name>.yml. Encrypted credentials go in the ignored
secrets/vault.yml. It is outside group_vars/ and is NOT loaded automatically by inventory.
No playbook loads it automatically. Add `-e @secrets/vault.yml --ask-vault-pass`
when the run needs saved SSH/sudo passwords or root password hashes.
See [VAULT.md](VAULT.md) for commands and loading rules.
SSH private keys remain outside this repository. Add only public keys to keys/.
No real passwords or public keys are prefilled.

Host exceptions: Hydra is OpenMediaVault, connects as root, and is in nas_appliances.
Baseline, root-access and network jobs exclude that group; the SSH-key and read-only
playbooks still include it. Biteforce's host_vars sets ansible_password to null,
overriding the shared Vault SSH-password expression even with bootstrap_password_auth=true. Its
host_vars selects the user-confirmed WSL key ~/.ssh/homelab_laptop. Load the key
into ssh-agent first if it has a passphrase.
See [HOST-EXCEPTIONS.md](HOST-EXCEPTIONS.md) for direct-SSH tests and mixed-run commands.

For the selected user-key -> root-access -> later-root sequence, follow
[ROOT-ACCESS.md](ROOT-ACCESS.md). The root job needs each selected VM's
root_password_hash in Vault and a controller private-key path for a fresh root
connection test. Later jobs select root explicitly with `-e ansible_user=root`;
the default stays the ordinary user until that VM has completed root setup.

VM logins use existing accounts: linux_vms.yml defaults `ansible_user` to the inventory
name (valkyrie, huge, etc.). Override it in host_vars when the actual username differs.
The key playbook manages that user's own authorized_keys without sudo. Package and
network-staging playbooks use sudo; the account must already have permission to do so.
Root SSH and root's password may stay locked. The sudo password is the user's password,
not root's. Supply it per VM as `sudo_password` in Vault, or use `--ask-become-pass`
for a single VM. Load saved sudo passwords with `-e @secrets/vault.yml --ask-vault-pass`
while SSH uses keys. Root/key and passwordless-sudo runs need neither flag.
Proxmox hosts retain their separate root login default in proxmox_hosts.yml; override
that host setting separately if needed. Guest-account changes do not alter host access.

Use `--limit` on every initial run. A guest playbook targeting linux_vms cannot configure
the Proxmox hosts. The host-side guest-agent playbook targets proxmox_hosts separately.
Inventory aliases are stable names such as valkyrie. `ansible_host` is the SSH address;
it can be an IP or a DNS name resolvable from the controller. `network_address` is
separately set to the guest's numeric IPv4 address and checked against its observed main
IPv4 address before network changes. It is never derived from the SSH address.
`vmid` is the current Proxmox VM ID; `proxmox_name` is the expected display name.
Keep both up to date if you recreate or rename a VM. The October 20 screenshot
provided the current IDs/names. No owning-node mapping is hardcoded.

The guest-agent option job is one file with four steps: read the cluster VM list,
read each selected VM's config, check it, and enable its agent option if disabled.
Select guests normally with `--limit valkyrie,huge`. All commands are delegated to
Endgame by default; use `-e proxmox_host=deepsix` to choose another entry host.
It finds the current node by VM ID, verifies the expected name, and refuses locked
VMs, templates or custom agent options. It includes the config digest to avoid
silently overwriting concurrent config edits. The separate lookup file is removed.
The job does not restart VMs or install packages. In --check mode it reads and
checks settings but skips the setting-change command; that command does not predict
changes. Working intra-cluster communication is required for remote API routing.

If you already made a Vault file using the earlier numbered aliases, rename its keys
to the new aliases with `ansible-vault edit`. Rename any matching host_vars files too.
See [the naming guide](NAMING.md) for the mapping and examples.

## Checks before use

```bash
ansible-inventory --graph
ansible-playbook playbooks/ssh-keys.yml --syntax-check
ansible-playbook playbooks/root-access.yml --syntax-check
ansible-playbook playbooks/baseline.yml --syntax-check
ansible-playbook playbooks/discover.yml --syntax-check
ansible-playbook playbooks/proxmox-agent.yml --syntax-check
ansible-playbook playbooks/network.yml --syntax-check
ansible-playbook playbooks/verify.yml --syntax-check
```

Syntax checks do not establish connectivity or that the desired settings are correct.
`--check` connects to targets and predicts supported changes; it is not an offline simulator.
Guest-agent service activation is skipped in check mode because a not-yet-installed unit
cannot be inspected. Commands generally cannot predict changes in check mode.

## Sources

* [Inventory and variables](https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html)
* [Ansible Vault](https://docs.ansible.com/projects/ansible/latest/vault_guide/index.html)
* [sudo and become passwords](https://docs.ansible.com/projects/ansible-core/devel/playbook_guide/playbooks_privilege_escalation.html)
* [Linux password hashes and account locking](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/user_module.html)
* [OpenSSH root and Match policy](https://man.openbsd.org/sshd_config)
* [Authorized keys](https://docs.ansible.com/projects/ansible/latest/collections/ansible/posix/authorized_key_module.html)
* [Proxmox VM configuration](https://pve.proxmox.com/pve-docs/qm.1.html)
* [Proxmox cluster resource fields](https://github.com/proxmox/pve-manager/blob/master/PVE/API2/Cluster.pm)
* [Proxmox pvesh routing implementation](https://github.com/proxmox/pve-manager/blob/master/PVE/CLI/pvesh.pm)
* [Netplan CLI and rollback](https://github.com/canonical/netplan/blob/main/doc/cli.md)
