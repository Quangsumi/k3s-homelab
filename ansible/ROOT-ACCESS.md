# Your sequence: user key first, root access second

The jobs are separate. You choose when to run each one.

```text
1. Log in as valkyrie using its current password.
2. Add your laptop key to valkyrie's account.
3. Log in as valkyrie using that key, then use sudo to prepare root access.
4. Test root access. Later jobs can log in directly as root using the key.
```

The first exercise in [LESSONS.md](LESSONS.md) covers steps 1 and 2.
The default VM account remains its name: valkyrie, huge, tombstone, and so on.
Hydra is an exception: it already uses root and is excluded from this root setup.
Biteforce connects as biteforce with your existing key, so it can enter at step 3
once its key connection and sudo are working. See [HOST-EXCEPTIONS.md](HOST-EXCEPTIONS.md).
The instructions below use the full inventory and its encrypted password file.

## 1. Add the key to your existing VM user

**Where: Ubuntu on your laptop, inside the project's ansible folder.**

```bash
ansible-playbook -i inventory/hosts.yml playbooks/ssh-keys.yml --limit valkyrie --ask-vault-pass -e bootstrap_password_auth=true -e @secrets/vault.yml
```

This uses `vault_hosts.valkyrie.ssh_password` to log in as `valkyrie`.
It adds `keys/laptop.pub` to that user's allowed keys. It does not use sudo or change root.

The [next lessons](NEXT-STEPS.md#1-let-ubuntu-use-your-existing-laptop-key) explain
how to make the matching private key available to Ubuntu and load its passphrase
with ssh-add. Confirm this works before proceeding:

```bash
ssh -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -i ~/.ssh/homelab_laptop valkyrie@192.168.63.22
```

Type `exit` to return to Ubuntu on your laptop.

## 2. Choose a root password

Your normal user's password and the new root password are separate choices.
Ansible needs a **hash** of the new root password: a one-way representation Linux
stores to check future logins. Keep the hash in Vault too.

**Where: Ubuntu on your laptop.**

```bash
openssl passwd -6
```

It prompts for the new root password and prints a value beginning with `$6$`.
Use the prompt rather than putting a real password in a command.
If OpenSSL is missing, install it with `sudo apt install openssl`.

Open your encrypted file:

```bash
EDITOR=nano ansible-vault edit secrets/vault.yml
```

Under the selected VM, keep the existing user's credentials and add the hash:

```yaml
vault_hosts:
  valkyrie:
    ssh_password: YOUR_EXISTING_VALKYRIE_PASSWORD
    sudo_password: YOUR_VALKYRIE_SUDO_PASSWORD
    root_password_hash: 'PASTE_THE_FULL_$6$_VALUE_HERE'
```

These uppercase strings are placeholders. The playbook refuses the placeholder
hash. If sudo does not ask your user for a password, omit sudo_password.
If sudo asks for your account password, that is normally the same as ssh_password.

Save and exit. Keep the same saved hash for later runs; generating a fresh hash
each time would cause Ansible to reset the password again even for the same password.

## 3. Prepare root access using your existing user

First check `sudo whoami` inside your normal VM session. It should print `root`.
The playbook needs that permission. It cannot grant itself sudo permission.

**Where: Ubuntu on your laptop.** Preview:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/root-access.yml --limit valkyrie --ask-vault-pass --private-key ~/.ssh/homelab_laptop -e "root_ssh_private_key_file=$HOME/.ssh/homelab_laptop" --check -e @secrets/vault.yml
```

`--private-key` is the key used to connect as valkyrie.
`root_ssh_private_key_file` tells the later root-login test where that same key is.
The test needs an unlocked key, so load a passphrase-protected key with ssh-add first.
This direct SSH test assumes the ordinary network path in our inventory; custom
ProxyJump, SSH configuration or unusual host-key aliases need matching test options.

The preview does not change root or test a new root login. It reads current state
and predicts the supported changes. To apply, run the same command without `--check`.

The job will:

1. Connect as your existing VM user and use sudo.
2. Add your selected public keys to root's allowed keys, preserving others.
3. Set the new root password and unlock its password entry.
4. Add a rule allowing root SSH by key **and password**. The rule is for root only.
5. Validate SSH's configuration, check its effective root settings, then reload SSH.
6. Open a separate root connection using your key and verify it really runs as root.

An earlier SSH rule may override the new rule. The job detects the effective settings
and stops instead of assuming that appending a line worked.
If the SSH configuration or new root connection fails, it restores the old SSH
configuration. Root's password and added keys remain set; those account changes
are not rolled back. Your original user's account and key stay available.

The saved SSH configuration backup path is reported by Ansible. Keep it until you
have checked both logins yourself. The job reloads SSH; it does not reboot the VM.

To set a root password but allow root SSH **only by key**, add:

```text
-e root_ssh_password_login=false
```

## 4. Test the root password too

The playbook automatically tests the key. To test the root password yourself:

```bash
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password root@192.168.63.22
```

Enter the new root password. If that works, run `exit`.
This test applies to the default policy that allows root password SSH, not the
key-only option above. PAM/account restrictions can still reject password login;
checking SSH settings alone does not prove a password login succeeds.

## 5. Choose root for a later job

For example, preview the package/guest-agent job using root and your key:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/baseline.yml --limit valkyrie --private-key ~/.ssh/homelab_laptop -e ansible_user=root --check
```

`-e ansible_user=root` means **use root for this run**.
The default inventory still uses your ordinary account. This keeps the initial
setup jobs usable for VMs where root access has not been enabled yet.
Do not add bootstrap_password_auth=true here: that flag selects the original
user's saved SSH password. Root uses the working key instead.

Do one VM first. After verifying each result, repeat with the next VM's name and
its own saved root_password_hash. A whole-group run needs credentials and keys
ready for every selected VM.
