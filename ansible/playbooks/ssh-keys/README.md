# SSH keys

Add or remove public keys for existing login accounts. Includes Linux VMs and
Proxmox hosts. Uses no sudo and preserves unrelated keys.

**Run from the `ansible` folder in WSL.** Shared setup: [GUIDE](../../GUIDE.md).

## Choose keys

Put public keys in `keys/`. Edit `inventory/group_vars/all/main.yml`:

```yaml
ssh_public_keys:
  - filename: laptop.pub
    state: present
  - filename: wsl.pub
    state: present
```

Only list files you actually supplied. `present` adds a key; `absent` removes it.
The task loops over this list. Each key goes into the login user's `authorized_keys`.
Private keys stay on their respective laptops/WSL installations.

## First installation using saved VM passwords

```bash
ansible-playbook playbooks/ssh-keys/main.yml -e @secrets/vault.yml --ask-vault-pass -e bootstrap_password_auth=true --check
ansible-playbook playbooks/ssh-keys/main.yml -e @secrets/vault.yml --ask-vault-pass -e bootstrap_password_auth=true
```

One command covers all selected hosts. Biteforce uses its existing key; Hydra and
Proxmox use root. Add `--limit linux_vms` to exclude Proxmox hosts.

## Later runs using your working key

```bash
ansible-playbook playbooks/ssh-keys/main.yml
```

No Vault is needed. To test key login without password fallback:

```bash
ssh -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no valkyrie@valkyrie.lab
```

The matching private key must be selected in WSL; see the shared guide.
For a first exercise without Vault, use the [minimal example](beginner/README.md).
