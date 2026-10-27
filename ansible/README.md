# Homelab Ansible

Run commands in **WSL Ubuntu**, from this `ansible` folder.
Ansible connects over SSH and applies the instructions in a playbook.

1. Read [Setup and reference](GUIDE.md) for installation, SSH keys, passwords and inventory.
2. Choose a job below. Each folder contains `main.yml` and its guide.
3. After the jobs work, read [Roles, handlers and dynamic inventory](ADVANCED.md) for the next concepts, with examples from this lab.

| Job | What it does |
|---|---|
| [SSH keys](playbooks/ssh-keys/README.md) | Add or remove public keys for existing login accounts |
| [Root access](playbooks/root-access/README.md) | Enable root keys, set its password and configure root SSH |
| [Baseline](playbooks/baseline/README.md) | Install common packages and the QEMU guest agent inside VMs |
| [Proxmox agent option](playbooks/proxmox-agent/README.md) | Enable the agent option in Proxmox VM settings |
| [Network](playbooks/network/README.md) | Change Ubuntu DNS with backup, verification and rollback |
| [Discover](playbooks/discover/README.md) | Read OS, interface and networking information |
| [Certificates](playbooks/certificates/README.md) | Copy public trust files to one Pi/control-plane host |
| [Verify](playbooks/verify/README.md) | Report addresses, routes, resolver and guest-agent status |

## Common command pattern

```bash
ansible-playbook playbooks/JOB/main.yml --check
ansible-playbook playbooks/JOB/main.yml
```

Replace `JOB` with a folder name above. `--check` previews supported changes;
it does not prove that the eventual change will work.

| Add this | To do this |
|---|---|
| `--limit valkyrie` | Select one VM |
| `--limit valkyrie,huge` | Select several VMs |
| `--limit workers` | Select an inventory group |
| No `--limit` | Select every host allowed by that playbook |
| `-e @secrets/vault.yml --ask-vault-pass` | Load saved credentials |
| `--ask-become-pass` | Type one shared sudo password instead |
| `-e ansible_user=root` | Use root for this run, after root access is ready |
| `--syntax-check` | Check Ansible syntax without running tasks |

SSH keys, root, baseline and network jobs process one host at a time automatically
and stop on failure. One command can cover the whole group.
Hydra/OMV is excluded from root, baseline and network jobs.

Certificates requires `--limit` matching exactly one host. See its job guide for preview and copy commands.
