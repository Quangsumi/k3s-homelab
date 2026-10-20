# VM names, IDs and SSH addresses

An entry now looks like this:

```yaml
valkyrie:
  vmid: 109
  ansible_host: valkyrie.lab
  network_address: 192.168.63.22
  proxmox_name: valkyrie
```

These settings answer different questions:

| Setting | Question it answers |
|---|---|
| `valkyrie` | What name do I type in an Ansible command? |
| `ansible_host` | Where does SSH connect? |
| `network_address` | Which IPv4 address should the guest's network configuration retain? |
| `vmid` | Which Proxmox VM should the job configure? |
| `proxmox_name` | Which name should that ID have, to check we found the right VM? |

The VM ID is stored in inventory. If it changes, update vmid. If the Proxmox display
name changes, update proxmox_name. The job discovers the current owning node each run.

`ansible_host` can be an IP or a DNS name. When using `valkyrie.lab`, that name must
resolve to the VM from Ubuntu, where Ansible runs. The active inventory keeps the
existing IP connection addresses until you choose to switch them to working DNS names.
`network_address` always stays a numeric IPv4 address, regardless of how SSH connects.
The network-staging job verifies it is already assigned to the guest; changing a
VM's actual IP is a separate operation, not part of this baseline.

VM SSH usernames default to the Ansible name too: `valkyrie` logs in as `valkyrie`.
To use a different existing account, create `inventory/host_vars/valkyrie.yml` with:

```yaml
ansible_user: your_actual_username
```

This selects an account that already exists; it does not create or rename a user.

IDs and lowercase names were updated from your October 20 Proxmox screenshot.
The job uses the ID to find the VM, then checks its name before changing a setting.

## Example: enable Valkyrie's guest-agent option

From Ubuntu, in the project's ansible folder:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/proxmox-agent.yml --limit valkyrie --private-key ~/.ssh/homelab_laptop
```

This selects the guest named valkyrie. Commands run through Endgame, the default
Proxmox entry host; it can reach either node in the cluster. To choose Deep Six as
the entry point, add `-e proxmox_host=deepsix`. To select several guests, use
`--limit valkyrie,huge` instead. No extra VM-selection variable is needed.

This key-based Proxmox run does not need Vault. If using the host's saved SSH
password instead, add `-e @secrets/vault.yml --ask-vault-pass -e bootstrap_password_auth=true`.
Valkyrie can be on either host: the playbook discovers its location and Proxmox routes the request there.
The Proxmox hosts must have working cluster communication for that routing.

## If you used the earlier files already

The Ansible names changed as follows. These are local configuration changes;
the VMs themselves have not been renamed.

| Earlier Ansible name | New Ansible name |
|---|---|
| tombstone100 | tombstone |
| whyachi101 | whyachi |
| biteforce107 | biteforce |
| huge104 | huge |
| minotaur106 | minotaur |
| valkyrie102 | valkyrie |
| hydra108 | hydra |

If you created `secrets/vault.yml`, open it with:

```bash
ansible-vault edit secrets/vault.yml
```

Change each name underneath `vault_hosts` to the new name above. Keep its password.
The example file is already updated. Any real encrypted file was left untouched.

If you made a file such as `inventory/host_vars/valkyrie102.yml`, rename it to
`valkyrie.yml`. Use the new names in your saved commands as well.
