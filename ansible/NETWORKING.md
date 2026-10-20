# Network changes without logging into every VM

The network job now backs up, validates, applies and checks the change itself.
**Start with Valkyrie. Hydra is excluded.** No VM network has been changed while
preparing these files.

## What this first version changes

It sets the DNS server list on the VM's main Ethernet interface. It preserves the
complete existing Netplan configuration: IP addresses, routes, IPv6, MAC matching,
interface naming and DNS search domains. It does not change IPs or convert DHCP to
static addressing. We can add deliberate address changes separately after DNS works.

Your discovery output reported ens18 and gateway 192.168.63.1 on all six Ubuntu VMs.
The job verifies these assumptions, and each VM's recorded network_address, before
changing anything. The IP is separate from ansible_host, which may be a DNS name.

## 1. Choose the DNS server and a name it should resolve

In inventory/group_vars/all/main.yml:

```yaml
network_dns:
  - 192.168.63.102
network_dns_test_name: tombstone.lab
```

The test name must exist on that DNS server. You can override either setting in a
VM's host_vars file. network_manage: false can exclude an ordinary VM by causing
its preflight check to stop the run; Hydra is already excluded by its inventory group.

## 2. Read the plan for one VM

From Ubuntu on your laptop, in the ansible folder:

```bash
ansible-playbook playbooks/network.yml --limit valkyrie -e @secrets/vault.yml --ask-vault-pass --check
```

This reads the existing Netplan configuration and cloud-init's recorded network
setting, then shows current versus desired DNS. It does not back up, install, apply
or arm a timer in check mode. Candidate validation happens before any live files
change during the real run. If DNS already matches, the real run also leaves it alone.

For passwordless sudo or root/key access, omit the Vault arguments. For a manually
typed sudo password instead, use --ask-become-pass without the Vault arguments.

## 3. Apply on that VM

Run the same command without --check:

```bash
ansible-playbook playbooks/network.yml --limit valkyrie -e @secrets/vault.yml --ask-vault-pass
```

The job performs these steps automatically:

1. Read the full merged Netplan settings and identify the correct Ethernet definition.
2. Change only its nameservers.addresses list in that preserved configuration.
3. Back up /etc/netplan and any previous Ansible cloud-init network setting under
   /root/backups/network/<unique-directory>/.
4. Write and validate a candidate outside /etc/netplan.
5. Install and arm a three-minute rollback timer inside the VM.
6. Replace overlapping Netplan files with the merged candidate, preserving their
   effective settings. If cloud-init is present and not recorded as network-disabled,
   write a setting disabling only its network generation. Other cloud-init functions remain.
7. Start netplan apply as a system service, independently of the SSH session.
8. Open a fresh SSH connection; wait for apply to finish; check the IP, gateway,
   effective DNS list and an uncached DNS lookup. Control planes also need a healthy
   local Kubernetes API before and after the change.
9. Commit the change and cancel rollback only after every check passes.

Existing runtime DHCP/IPv6 DNS servers may add to the effective list. If that prevents
it matching the intended list, verification fails and restores the old configuration;
review those existing settings rather than disabling DHCP/IPv6 blindly.

## What if the network breaks?

The timer belongs to the VM, so disconnecting SSH does not cancel it. It stops a
still-running apply operation, restores the saved Netplan files and previous
Ansible cloud-init setting, then reapplies the old network. If an ordinary task fails
while SSH still works, the playbook requests rollback immediately.

A small helper, files/network-rollback.sh, is necessary because recovery must work
without Ansible's connection. A lock and marker files prevent a late timer from
undoing a committed change or reporting an already-rolled-back change as committed.

A failed/unreachable VM stops the rollout. Wait for recovery and verify it before
rerunning. The job does not power-cycle VMs. The transient timer does not survive a
reboot or repair a frozen VM: keep Proxmox console access available as the fallback.

If needed from that console, run the saved helper using the backup path printed
by Ansible (replace BACKUP_PATH):

```bash
/bin/sh BACKUP_PATH/rollback.sh BACKUP_PATH
```

The helper does nothing once committed. For a deliberate reversal of an already
committed change, review and restore the retained backup as a separate operation.

## Biteforce and Hydra

**Biteforce:** cloud-init and Netplan are compatible stages of the original setup.
The job preserves its existing MAC/set-name rules instead of writing a minimal
replacement. Its existing key-login and /usr/bin/sudo override stay in host_vars.

**Hydra:** OpenMediaVault generates its Netplan files. The generic network job never
selects nas_appliances. Use OMV's network settings for its DNS and static address.

## Expand after the first VM succeeds

```bash
ansible-playbook playbooks/network.yml --limit workers -e @secrets/vault.yml --ask-vault-pass
```

The job uses serial: 1: finish and verify one VM before starting another. Do control
planes separately after the first worker changes are verified. No manual SSH backup
or netplan apply commands are needed for the normal workflow.
