# Root access

Connect as the existing VM user, use sudo, then configure root.
Hydra is excluded. Complete the [SSH-key job](../ssh-keys/README.md) first.

**Run from the `ansible` folder in WSL.** Shared setup: [GUIDE](../../GUIDE.md).

## 1. Save a root password hash

Generate a hash; enter the desired root password at the prompt:

```bash
openssl passwd -6
EDITOR=nano ansible-vault edit secrets/vault.yml
```

Add the complete printed `$6$...` value under each selected VM:

```yaml
vault_hosts:
  valkyrie:
    sudo_password: YOUR_EXISTING_USER_PASSWORD
    root_password_hash: 'PASTE_FULL_HASH_HERE'
```

Keep any existing fields. Reuse the saved hash on later runs.
Root's password is separate from the existing user's password.

## 2. Preview, then apply

```bash
ansible-playbook playbooks/root-access/main.yml -e @secrets/vault.yml --ask-vault-pass -e "root_ssh_private_key_file=$HOME/.ssh/homelab_laptop" --check
ansible-playbook playbooks/root-access/main.yml -e @secrets/vault.yml --ask-vault-pass -e "root_ssh_private_key_file=$HOME/.ssh/homelab_laptop"
```

All selected VMs need hashes and working sudo. Add `--limit valkyrie` for an optional
single-VM test. Unlock a passphrase-protected private key with `ssh-add` first.

| Custom variable | Purpose |
|---|---|
| `root_ssh_password_login` | Defaults to `true`: root SSH accepts keys or passwords. Set `-e root_ssh_password_login=false` for key-only root SSH. |
| `root_ssh_private_key_file` | Private key on WSL used by the final, separate root-login test. It is not copied to VMs. |

The job adds root's public keys, sets/unlocks its password, validates root-only SSH
rules, reloads SSH and tests a fresh key login. Check mode does not test the new login.
The direct test uses the specified key; unusual proxy/host-alias setups need matching options.

On configuration/test failure, the original SSH configuration is restored.
The added root keys and password remain set. The original user remains available.

## 3. Use root later

```bash
ansible-playbook playbooks/baseline/main.yml -e ansible_user=root --check
```

No saved sudo password is needed for root. Inventory still defaults to the existing
user so bootstrap remains usable. Leave `bootstrap_password_auth` false.

To test root's password manually, use the password chosen in step 1:

```bash
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password root@valkyrie.lab
```

The playbook tests key access automatically; it does not prove password authentication succeeds.
