# Hydra and Biteforce connect differently

The shared settings are defaults, not a requirement that every VM works the same way.
A file under `inventory/host_vars/` supplies settings for just that machine.

| Machine | Account | How Ansible logs in initially |
|---|---|---|
| Most VMs | Their name, such as tombstone | Existing password, then your key |
| Hydra | root | Existing root password, then your key |
| Biteforce | biteforce | Your existing laptop key from the start |

## Hydra: OpenMediaVault

`inventory/host_vars/hydra.yml` sets `ansible_user: root`.
In Vault, `vault_hosts.hydra.ssh_password` must be the existing root SSH password.
It is not the web interface's administrator password unless you deliberately made
those passwords the same. No hydra user is created and no sudo password is needed.

Preview its SSH-key change from Ubuntu:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/ssh-keys.yml --limit hydra --ask-vault-pass -e bootstrap_password_auth=true --check --diff -e @secrets/vault.yml
```

This now targets root's allowed keys. Remove `--check --diff` when ready to apply.
This key job does not rewrite the NAS's SSH service configuration.

Hydra belongs to `nas_appliances`. Generic package/guest-agent installation, root
setup and Netplan staging explicitly exclude that group, even when you choose all
VMs. A Debian-based appliance still has its own configuration system. Use OMV's
supported settings for its DNS, static address and SSH policy; any guest-agent
installation there needs its own reviewed OMV procedure.

Read-only discovery/verification and the key job still include Hydra. The Proxmox-side
guest-agent option can also be selected separately; enabling it is different from
installing software inside OMV.

## Biteforce: use the key it already trusts

Your pasted run used password bootstrap without explicitly selecting a private key.
The server replied `Permission denied (publickey)`. That means it offered public-key
authentication, but the client did not authenticate successfully. The message alone
does not prove which key or username would succeed.

`inventory/host_vars/biteforce.yml` contains:

```yaml
ansible_user: biteforce
ansible_password: null
ansible_ssh_private_key_file: ~/.ssh/homelab_laptop
```

`ansible_password: null` means do not supply a saved SSH password for this host.
This host setting overrides the shared password expression, even when you enable
password bootstrap for other VMs. Ansible uses the selected key for Biteforce.
There is no extra password-login flag or custom SSH option list to understand.
This does not change the VM's SSH settings or cloud-init configuration.
Your successful WSL command confirmed `~/.ssh/homelab_laptop` works. That path is
now saved as `ansible_ssh_private_key_file` in Biteforce's settings, so the mixed
run selects it automatically. To change it later, edit that file or override
`ansible_ssh_private_key_file` with `-e`; an inventory key setting takes precedence
over the general `--private-key` option.

Ansible runs inside Ubuntu/WSL. A key available to Windows SSH is not automatically
available to Ubuntu's SSH client.

First, confirm the key is available in Ubuntu. These examples use the copy described
in NEXT-STEPS.md, `~/.ssh/homelab_laptop`. Substitute your actual private-key path if
it has another name; the private key is the file WITHOUT `.pub`.

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/homelab_laptop biteforce@192.168.63.67
```

If that fails, fix this direct connection before running Ansible. Common causes:
the key file has not been copied into WSL, the selected key is different from the
one installed in Biteforce, or the key needs unlocking. The bare command
`ssh biteforce@192.168.63.67` does not explicitly select this custom key filename.

If your private key has a passphrase, load it in this Ubuntu terminal:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/homelab_laptop
```

After direct SSH works, type `exit`, then preview:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/ssh-keys.yml --limit biteforce --private-key ~/.ssh/homelab_laptop --check --diff
```

No `ssh_password` is needed for Biteforce in Vault. Keep `sudo_password` there only
if its existing user needs a password for sudo. The optional root-access playbook
can use this working key and sudo later; it does not need the original user's
password SSH enabled.

## A mixed run after testing both hosts

```bash
ansible-playbook -i inventory/hosts.yml playbooks/ssh-keys.yml --ask-vault-pass --private-key ~/.ssh/homelab_laptop -e bootstrap_password_auth=true --check --diff -e @secrets/vault.yml
```

For hosts supporting password login, Ansible has their saved passwords available.
Biteforce uses its selected key without a saved SSH password. Hydra logs in as root.
All other login usernames remain unchanged.

Because this is a preview, `changed` means a change is proposed. Your pasted run
did not add the proposed keys to Tombstone, Whyachi or Minotaur. Huge and Valkyrie
reported that the requested key state already matched. Test the two exceptions
separately, then review the full preview before removing `--check --diff`.

## Documentation

* [OpenMediaVault SSH defaults and settings](https://docs.openmediavault.org/en/7.x/administration/services/ssh.html)
* [OpenMediaVault network management](https://docs.openmediavault.org/en/8.x/administration/general/network.html)
* [Cloud-init password authentication settings](https://docs.cloud-init.io/en/latest/reference/modules.html)
