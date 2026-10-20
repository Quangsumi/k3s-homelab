# Ubuntu DNS

Change the main interface's DNS servers. Preserve existing IP addresses, routes,
IPv6, interface naming and DNS search domains. Hydra/OMV is excluded.
This version does not change IPs or convert DHCP to static addressing.

**Run from the `ansible` folder in WSL.** Shared setup: [GUIDE](../../GUIDE.md).

## Settings

In `inventory/group_vars/all/main.yml`:

```yaml
network_dns:
  - 192.168.63.102
network_dns_test_name: tombstone.lab
network_interface: ens18
network_gateway: 192.168.63.1
network_rollback_seconds: 180
```

The test name must exist on the selected DNS server. Each inventory host also has
its expected numeric `network_address`. Override differing settings in its host file.
`network_manage: false` makes the preflight stop; it does not silently skip that VM.

## Preview all supported VMs

```bash
ansible-playbook playbooks/network/main.yml -e @secrets/vault.yml --ask-vault-pass --check
```

## Apply all supported VMs

```bash
ansible-playbook playbooks/network/main.yml -e @secrets/vault.yml --ask-vault-pass
```

One command processes the VMs automatically, one after another. You do not need to
SSH into each VM, back up files or run `netplan apply` yourself.
An optional first test adds `--limit valkyrie` to either command.
Omit Vault flags if your login needs no sudo password.

## What happens

1. Read merged Netplan settings and match the interface, including MAC-based names.
2. Change only its DNS list; retain the other effective settings.
3. Back up under `/root/backups/network/` and validate a candidate outside `/etc/netplan`.
4. Arm a rollback timer **inside the VM**, then install the merged configuration.
5. Disable cloud-init network generation where needed; other cloud-init functions remain.
6. Apply through a local service, open fresh SSH and verify IP, gateway and DNS.
7. Check an uncached DNS lookup; control planes also need local K3s readiness.
8. Commit and cancel rollback only after checks pass; otherwise stop the rollout.

Check mode reads and shows the proposal. It does not create backups, validate a
staged candidate or apply changes. Matching configured DNS means no change is made.
Runtime DHCP/IPv6 DNS additions can cause strict DNS verification to fail and roll back.

## If SSH drops

The local timer still runs. After 180 seconds it attempts to restore the old files
and reapply them. If a task fails while SSH works, rollback is requested immediately.
The helper lives at `files/network-rollback.sh` beside this playbook.

A transient timer does not survive reboot or fix a frozen VM. Keep Proxmox console
access available as a fallback. This recovery has not yet been tested live.

For an uncommitted change, run from the VM console if needed, using its backup directory:

```bash
/bin/sh BACKUP_PATH/rollback.sh BACKUP_PATH
```

A committed change is not undone by this helper. Its retained backup can be reviewed
for a separate reversal. Verify recovery before retrying a failed rollout.

## Why the different Netplan files?

| File | Usual writer |
|---|---|
| `00-installer-config.yaml` | Ubuntu installer |
| `50-cloud-init.yaml` | Cloud-init |
| `90-ansible.yaml` | This playbook |
| `*-openmediavault-*.yaml` | OMV; leave Hydra under OMV control |

Netplan combines files in filename order; lists can accumulate. The job backs up
and consolidates the effective configuration into `90-ansible.yaml` rather than
adding overlapping DNS lists. Biteforce's existing MAC/set-name rules are retained.
