# Setup and quick reference

All Bash commands run in **WSL Ubuntu on your laptop**, from the `ansible` folder.
Do not run them inside a VM. Playbook-specific commands are beside each playbook.

## 1. Install once

If Ubuntu is missing, run `wsl --install -d Ubuntu` in administrator PowerShell,
then open Ubuntu and create its local account.

In Ubuntu, use Python 3.11 or newer:

```bash
sudo apt update
sudo apt install -y python3 python3-venv openssh-client sshpass openssl
cd '/mnt/d/OneDrive/Desktop/Side Quests/PETs/k3s-homelab/ansible'
python3 -m venv ~/.venvs/homelab-ansible
source ~/.venvs/homelab-ansible/bin/activate
python -m pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
ansible --version
```

The `config file` line should point to this project's `ansible.cfg`.
`venv` keeps Ansible's Python packages separate from Ubuntu's own packages.

## 2. Each new terminal

```bash
source ~/.venvs/homelab-ansible/bin/activate
cd '/mnt/d/OneDrive/Desktop/Side Quests/PETs/k3s-homelab/ansible'
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
```

## 3. Make your SSH key available in WSL

Windows and WSL have separate home folders and SSH settings.
Keep the private key in WSL's `~/.ssh/`, outside this project.
Copy only its matching **public** key into `keys/laptop.pub`.

For example, if your existing Windows key is named `homelab_laptop`:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cp '/mnt/c/Users/Mike Hawk/.ssh/homelab_laptop' ~/.ssh/homelab_laptop
chmod 600 ~/.ssh/homelab_laptop
cp '/mnt/c/Users/Mike Hawk/.ssh/homelab_laptop.pub' keys/laptop.pub
```

Use your actual source filenames. Do not overwrite an existing WSL key.
For a separate WSL key, generate it with `ssh-keygen -t ed25519`, then add its
`.pub` file using the [SSH-key job](playbooks/ssh-keys/README.md).

To avoid typing `--private-key` each time, add to `~/.ssh/config`:

```sshconfig
Host *.lab 192.168.63.*
    IdentityFile ~/.ssh/homelab_laptop
    IdentitiesOnly yes
```

If the private key has a passphrase, unlock it for this terminal:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/homelab_laptop
```

## 4. Trust the VM's identity

A **host key** identifies the VM. Your **login key** identifies you.
They are separate things.

For the first connection, SSH asks whether to trust the VM's fingerprint.
You can check it in the Proxmox VM console:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Connect from WSL using the same name or IP as `ansible_host` and compare the fingerprint.
For initial setup across many hosts, this accepts previously unseen host keys
while still rejecting changed keys; first-contact identity is not independently verified:

```bash
export ANSIBLE_SSH_COMMON_ARGS='-o StrictHostKeyChecking=accept-new'
```

Undo that terminal override with `unset ANSIBLE_SSH_COMMON_ARGS`.
Do not disable host-key checking globally.

## 5. Inventory and variables

| File | Purpose |
|---|---|
| `ansible.cfg` | Project settings; selects `inventory/hosts.yml` |
| `inventory/hosts.yml` | Hosts, groups, SSH addresses and Proxmox VM IDs |
| `inventory/group_vars/all/main.yml` | Defaults for all inventory hosts |
| `inventory/group_vars/linux_vms.yml` | Guest login and sudo settings |
| `inventory/group_vars/proxmox_hosts.yml` | Proxmox login settings |
| `inventory/host_vars/NAME.yml` | Overrides for one inventory host |
| `secrets/vault.yml` | Your encrypted credentials; loaded explicitly |
| `keys/*.pub` | Public keys to install |

Ansible automatically finds `group_vars` and `host_vars` beside the inventory.
A host setting overrides a group setting. Command-line `-e` variables override both.

```yaml
tombstone:                       # inventory_hostname: stable inventory alias
  ansible_host: tombstone.lab     # SSH destination; a working DNS name or IP
  network_address: 192.168.63.20  # Expected numeric guest IP
  vmid: 100                      # Used only for Proxmox VM operations
  proxmox_name: tombstone        # Expected Proxmox name; catches wrong VM IDs
```

Use `--limit tombstone` even if its IP or Proxmox node changes.
Update `vmid` if the VM ID changes. DNS names must already resolve from WSL;
changing `ansible_host` does not create DNS records or change the VM's IP.
A login public key works whether you connect by IP or DNS name.

| Name | Meaning |
|---|---|
| `ansible_user` | Built-in connection setting: remote login account |
| `ansible_password` | Built-in connection setting: SSH login password |
| `ansible_become_password` | Built-in setting: sudo password |
| `inventory_hostname` | Ansible's current inventory alias |
| `vault_hosts` | Our custom dictionary of credentials |
| `bootstrap_password_auth` | Our switch for supplying saved SSH passwords |

Before running a remote task, Ansible resolves that host's connection variables,
then opens SSH. That is where `ansible_password` is used; modules do not call it.
The shared expression supplies it only when `bootstrap_password_auth=true`.
After key setup, leave that switch false. Sudo may still need a password.

## 6. Store credentials in Vault

The Vault password unlocks the encrypted file. It is separate from VM passwords.
Create the file if absent:

```bash
EDITOR=nano ansible-vault create secrets/vault.yml
```

Example structure; replace the illustrative values:

```yaml
vault_hosts:
  valkyrie:
    ssh_password: password01
    sudo_password: password01
  huge:
    ssh_password: password02
    sudo_password: password02
```

SSH authenticates the connection. Sudo grants administrator permission afterward.
For the same normal user these passwords are usually identical. Omit passwords
that are not needed, such as `sudo_password` for passwordless sudo.

| Situation | What to add to the playbook command |
|---|---|
| Working key; no sudo password needed | Nothing |
| Working key; saved sudo password needed | `-e @secrets/vault.yml --ask-vault-pass` |
| First key installation using saved SSH passwords | Both flags above plus `-e bootstrap_password_auth=true` |

`--ask-vault-pass` only supplies the decryption password; `-e @...` loads the file.

```bash
# Edit an encrypted file:
EDITOR=nano ansible-vault edit secrets/vault.yml
# Encrypt an existing plain YAML file, then edit it:
ansible-vault encrypt secrets/vault.yml
```

If `create` says the file exists but `edit` says it is not encrypted, it is plain
or empty. Open it locally, check its contents, then use `encrypt`; do not delete credentials.

## 7. Lab exceptions

| Host | Login | Special handling |
|---|---|---|
| Most guests | Same as inventory alias | Existing user; sudo for admin jobs |
| Biteforce | `biteforce`, existing key | Saved SSH password disabled; uses `/usr/bin/sudo` |
| Hydra | `root` | OMV owns networking; excluded from generic root/baseline/network jobs |
| Proxmox hosts | `root` | Separate group; SSH-key job includes them |

Ubuntu guests default to `/usr/bin/sudo.ws` because the observed sudo-rs prompt
caused Ansible timeouts. Biteforce overrides this to `/usr/bin/sudo`.
Change the per-host override if its installed sudo differs.

## 8. Read a playbook and its results

| Setting/output | Meaning |
|---|---|
| `hosts` | Inventory hosts selected for the play |
| `tasks` | Ordered steps |
| `become: true` | Use sudo; `false` runs as the SSH user |
| `serial: 1` | Finish one host before starting the next, automatically |
| `any_errors_fatal: true` | Stop the rollout if a host fails |
| `assert` | Stop if a required condition is false |
| `loop` / `item` | Repeat a task for each list entry / the current entry |
| `loop_control.label` | Short display label; does not change the loop |
| `ok` | Requested state already matched |
| `changed` | Updated something; in check mode, predicts an update |
| `failed` / `unreachable` | Stop and inspect the error |

Gathering facts runs before normal tasks when enabled. It can fail on SSH/sudo
before the first explicit assertion. A failed assertion stops later tasks for that host;
our serial jobs also stop the broader rollout.

## Troubleshooting

| Error | Check |
|---|---|
| Password SSH blocked by host-key checking | Trust the fingerprint, or use the initial `accept-new` option above |
| `Permission denied (publickey)` | WSL has the correct private key and username; try direct SSH |
| Sudo prompt timeout | Correct sudo password and executable; see lab exceptions |
| `/usr/bin/sudo.ws: not found` | Override that host with `ansible_sudo_exe: /usr/bin/sudo` |
| Unexpected Vault prompt | Load Vault only for jobs needing saved credentials |
| DNS hostname fails | Check name resolution from WSL, or use the known IP |

Return to the [job list](README.md).

Once the individual jobs make sense, continue with [roles, handlers and dynamic inventory](ADVANCED.md).
