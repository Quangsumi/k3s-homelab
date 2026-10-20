# After the first VM works

Work through one section at a time. Each section builds on the previous result.
All commands below run in Ubuntu on your laptop unless a different location is stated.

## 1. Let Ubuntu use your existing laptop key

The first exercise proved key login from Windows. Ansible runs in Ubuntu, so Ubuntu
also needs access to that same private key.

The following example copies your existing key into Ubuntu's own home folder.
It does not put it in the project. Use the filename matching your public key.

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cp '/mnt/c/Users/Mike Hawk/.ssh/id_ed25519' ~/.ssh/homelab_laptop
chmod 600 ~/.ssh/homelab_laptop
```

`mkdir -p` creates the folder if needed. `cp` copies the key. The `chmod` commands
restrict access to your Ubuntu user. Skip the copy if you already have the correct
key configured there; do not overwrite a different key.

If your key has a passphrase, load it into an SSH helper:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/homelab_laptop
```

`ssh-agent` holds the unlocked key for this session. `ssh-add` asks for its passphrase.

Test without allowing VM-password fallback:

```bash
ssh -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -i ~/.ssh/homelab_laptop valkyrie@192.168.63.22
```

After a successful login, run `exit`. Now try Ansible using that key:

```bash
ansible-playbook -i beginner/hosts.yml beginner/add-key.yml --private-key ~/.ssh/homelab_laptop
```

**Expected result:** no VM-password prompt, no failed tasks, and normally `changed=0`.
`--private-key` tells Ansible which key to use.

## 2. Move from the exercise to the full machine list

If your chosen sequence is **user key -> enable root access -> later jobs as root**,
follow [ROOT-ACCESS.md](ROOT-ACCESS.md). The sections below also support keeping
root locked and using your ordinary account with sudo throughout.

Open `inventory/hosts.yml`. It contains the seven VMs from the lab notes and both
Proxmox hosts. Addresses need confirming before use.

The name `valkyrie` stays the same in the full list. Names do not include VM IDs.
Hydra uses root and Biteforce uses a key from the start; their individual settings
are explained in [HOST-EXCEPTIONS.md](HOST-EXCEPTIONS.md).

Each VM also has `proxmox_name`, for example `Valkyrie`. That must exactly match
its display name in Proxmox, including capital letters. It is used only for changing
Proxmox settings. SSH jobs still connect to the address in `ansible_host`.

```bash
ansible-inventory -i inventory/hosts.yml --graph
```

You should see machines grouped under names such as `workers`, `control_planes`
and `proxmox_hosts`. A group lets you select several machines by one name.

Open `inventory/group_vars/all/main.yml`. Ansible automatically reads settings in
this location for machines in this inventory. Think of it as shared settings.
`inventory/group_vars/linux_vms.yml` sets each VM login user to its inventory name:
`valkyrie` connects as `valkyrie`, `huge` as `huge`. If a username is different, put
`ansible_user: actual_username` in that VM's host_vars file.
Hydra already has that override: it connects as root. Biteforce's host file sets
`ansible_password: null` and selects its existing key, so it does not use the saved
bootstrap password even when you enable password bootstrap for other VMs.
For example:

```yaml
ssh_public_keys:
  - filename: laptop.pub
    state: present
```

This says our allowed-key list contains `laptop.pub`.
The full `playbooks/ssh-keys.yml` repeats its key task for each entry in this list.
That repetition is called a **loop**.

Try the full job on the same VM first:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/ssh-keys.yml --limit valkyrie --private-key ~/.ssh/homelab_laptop
```

`--limit valkyrie` restricts this run to that VM. It should not change anything
if the first exercise already added the same key.

Key-only jobs and inventory display do not need the Vault password. Secrets now
live in `secrets/vault.yml`, outside the automatically loaded inventory folders.
Add `-e @secrets/vault.yml --ask-vault-pass` only when a job needs the saved
SSH/sudo passwords or root password hashes. See [VAULT.md](VAULT.md) for the commands.

## 3. Store different passwords for the remaining VMs

One VM was easy: you typed its password. For several VMs with different passwords,
we will let Ansible look up the correct password for each machine.

The passwords go into an encrypted file. Ansible's encryption tool is called **Vault**.
Vault's password unlocks that file; it is different from the VM passwords inside it.

```bash
EDITOR=nano ansible-vault create secrets/vault.yml
```

Choose a password for the encrypted file. The Nano editor then opens.
Enter your real credentials using the structure in `vault.example.yml`, for example:

```yaml
vault_hosts:
  tombstone:
    ssh_password: password01
    sudo_password: password01
  whyachi:
    ssh_password: password02
    sudo_password: password02
```

Those are illustrative passwords. Replace them. Include each machine you intend to
connect to by password. Use its exact name from `inventory/hosts.yml`.
`ssh_password` opens the SSH connection. `sudo_password` lets the same account run
administrator tasks inside the VM. Usually both are your account password, as shown.
Neither is root's password. Omit `sudo_password` if your user has passwordless sudo.
Save with Ctrl+O, press Enter, and exit with Ctrl+X. Vault encrypts the saved file.
If Nano is unavailable, install it with `sudo apt install nano`.

To change the passwords later:

```bash
EDITOR=nano ansible-vault edit secrets/vault.yml
```

Now add the laptop key to one more VM, after checking its address and SSH identity:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/ssh-keys.yml --limit huge --ask-vault-pass -e bootstrap_password_auth=true -e @secrets/vault.yml
```

`-e @secrets/vault.yml` loads the encrypted variables.
`--ask-vault-pass` asks for its decryption password.
`-e bootstrap_password_auth=true` tells SSH to use the saved login passwords.

The shared settings select `vault_hosts.huge.ssh_password` for Huge. Tombstone
would select its own entry. You do not need to understand the lookup expression yet.

Test a new key-only SSH connection to Huge, as you did for Valkyrie. Repeat this
one-VM process for the other machines before attempting a whole-group run.

This project keeps the encrypted password file out of Git. Keep your Vault password
separately. File encryption does not stop OneDrive from syncing the encrypted file.

## 4. Inspect a VM before installing things

Ansible can ask the VM about its operating system and network settings.
It calls this information **facts**.

```bash
ansible-playbook -i inventory/hosts.yml playbooks/discover.yml --limit valkyrie --private-key ~/.ssh/homelab_laptop
```

**Expected result:** information about the OS, network interfaces and configuration
files. This job reads information; it does not change networking.

Confirm the OS before managing packages. A NAS appliance may require its own
settings interface, even if ordinary Linux commands are available inside it.

## 5. Install software and keep a service running

Your user can edit its own SSH keys. Installing software needs administrator
permission. Ansible logs in as your user, then uses **sudo** for those tasks.
`become: true` in a playbook means use that administrator permission. Root login
can remain locked. Your existing user must already be allowed to use sudo.

To check that permission yourself, log into the VM as usual and run:

```bash
sudo whoami
```

It should print `root` after accepting your account password. That means sudo works;
it does not mean you enabled root login. If permission is denied, the account needs
sudo access before package or network jobs can work. The key exercise can still work.

For one VM without a stored sudo password, add `--ask-become-pass` to an administrative
playbook command. Ansible asks for your user's sudo password. For several VMs with
different passwords, store each `sudo_password` in Vault instead. Add
`-e @secrets/vault.yml --ask-vault-pass` to load it while SSH itself uses a key.

The full job for common software is `playbooks/baseline.yml`.
A **package** is installable software. A **service** is a program that runs in the background.

Here is the package task in plain English:

```yaml
ansible.builtin.package:
  name: qemu-guest-agent
  state: present
```

It means: make sure the guest-agent software is installed. If it is already
installed, leave it installed. `present` does not request a full OS upgrade.

The guest agent lets Proxmox communicate with the VM, for example to request
information or an orderly shutdown. It needs two things:

1. The guest-agent option enabled in that VM's Proxmox settings.
2. The guest-agent program installed and running inside the VM.

Inventory now records each guest's VM ID and expected Proxmox name. For Valkyrie,
they are `vmid: 109` and `proxmox_name: valkyrie`.

Run the option job for one guest:

```bash
ansible-playbook playbooks/proxmox-agent.yml --limit valkyrie
```

Or several guests:

```bash
ansible-playbook playbooks/proxmox-agent.yml --limit valkyrie,huge
```

The job connects to Endgame, reads the cluster list to find each VM's current node,
checks its settings, and enables the option only if needed. Your SSH key must already
work on Endgame. You can add `-e proxmox_host=deepsix` to use Deep Six instead.
For a saved Proxmox-host SSH password, also add
`-e @secrets/vault.yml --ask-vault-pass -e bootstrap_password_auth=true`.
If a VM's ID changes later, update vmid in inventory. If its name changes, update
proxmox_name. There is no separate lookup file or target_vm parameter.

This job enables the option but does not stop or restart a VM. A planned stop/start may be needed before
a newly added agent connection is available inside the running VM.

Then preview software installation inside Valkyrie:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/baseline.yml --limit valkyrie --ask-vault-pass -e @secrets/vault.yml --private-key ~/.ssh/homelab_laptop --check
```

Read the results. Remove `--check` to perform the installation when ready.
The service-start step is skipped during preview: Ansible cannot test a service
that may not be installed yet. If starting it fails during the real run, check that
the Proxmox connection is available; do not assume the software installed incorrectly.

## 6. Understand DNS and static IPs before editing them

An IP address is how other machines reach the VM. A **static IP** is an address
configured to stay fixed inside that VM. A router can also give a VM a fixed
address using a DHCP reservation; that is a different way to achieve a stable address.

DNS translates names to addresses. A VM's **DNS server setting** tells it where to
ask those questions. It does not automatically create a name for the VM on that server.

The proposed DNS server here is `192.168.63.102`. Confirm it is correct and reachable.
We preserve the VMs' existing addresses, especially the Kubernetes nodes.

Different Linux systems store network settings differently. **Netplan** is one
such configuration tool. We need to identify what your VM uses before writing files.

Read [NETWORKING.md](NETWORKING.md) once the earlier steps work. The job changes
DNS automatically while preserving the existing network configuration. It backs up,
validates and applies the change, then reconnects and checks it. A timer on the VM
restores the old files if verification cannot complete. No per-VM manual backup or
netplan apply is needed. Hydra remains managed through OpenMediaVault.

## 7. Reuse settings without copying the whole job

Suppose every VM uses the same DNS server, but each has a different address.
Put the common DNS setting in `inventory/group_vars/all/main.yml`.
Put any per-VM DNS override in `inventory/host_vars/valkyrie.yml`.

A **variable** is a named setting. For example:

```yaml
network_dns:
  - 192.168.63.102
```

The network job reads each VM's existing Netplan settings, changes just the DNS
list, and writes the resulting YAML. We no longer replace it with a minimal template
that might lose IPv6 or MAC-based naming. Variables let us reuse the instructions
while supplying the correct values for each VM.

## 8. Verify, then expand

```bash
ansible-playbook -i inventory/hosts.yml playbooks/verify.yml --limit valkyrie --private-key ~/.ssh/homelab_laptop
```

This reads the agent's service state, IP addresses, routes and resolver file.
Check the result against what you intended. A working SSH connection alone does
not prove DNS or the guest agent works. Also test an internal hostname and check
Proxmox can communicate with the agent.

Once each selected VM's access and OS are confirmed, `--limit workers` selects
the worker group. The jobs process one VM at a time and stop after an error.
They do not automatically prove that Kubernetes is healthy after each change.
Do control-plane changes separately with the cluster's health checks.

## 9. Add or remove a laptop later

Add another public key file under `keys/`, then add another item:

```yaml
ssh_public_keys:
  - filename: laptop.pub
    state: present
  - filename: second-laptop.pub
    state: present
```

Run the full key playbook on a selected VM and test the new laptop's access.

To remove an old key, keep its public file and change its `state` to `absent`.
Run the job using another working key. Deleting the item from your settings alone
would stop managing it; it would not remove the key already stored on the VMs.

## 10. What comes after that?

When the task files get large, you can organize related tasks into **roles**.
For example, one role could hold all the tasks and files for SSH access.

A **handler** is a task that runs when another task reports a change. For example,
a changed service configuration can trigger a service restart. Avoid using a
network-restart handler until you have a tested way to reconnect and recover.

A **dynamic inventory** builds the machine list from another system, such as
Proxmox, rather than requiring you to update the address book manually.

These become useful after you understand and can verify the smaller jobs above.
