# Proxmox guest-agent option

Enable the QEMU guest-agent checkbox in Proxmox VM settings.
This does not install software inside the VM; use [baseline](../baseline/README.md) for that.

**Run from the `ansible` folder in WSL.** Shared setup: [GUIDE](../../GUIDE.md).

```bash
ansible-playbook playbooks/proxmox-agent/main.yml --check
ansible-playbook playbooks/proxmox-agent/main.yml
```

One command covers all inventory VMs, including Hydra. To select some:

```bash
ansible-playbook playbooks/proxmox-agent/main.yml --limit valkyrie,huge
```

The job SSHs to `endgame` by default, discovers the VM's current node using its
`vmid`, checks `proxmox_name`, and enables the option if disabled.
VM migration between cluster nodes does not require an inventory owner change.
Update inventory if the ID or expected name changes.

| Option | Purpose |
|---|---|
| `-e proxmox_host=deepsix` | Use Deepsix as the Proxmox SSH entry point |
| `-e @secrets/vault.yml --ask-vault-pass -e bootstrap_password_auth=true` | Supply the entry host's saved SSH password if needed |

Locks, templates, unexpected names and custom agent options stop the job for review.
Check mode reads current settings and skips the actual update.
A VM may need a shutdown/start for the virtual agent channel to appear;
this playbook does not restart VMs. Verify communication in Proxmox afterward.
