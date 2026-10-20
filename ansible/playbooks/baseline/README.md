# Baseline packages and guest agent

Install `baseline_packages`, install `qemu-guest-agent`, then start the agent.
Enable automatic startup where its service supports enabling. Hydra is excluded.

**Run from the `ansible` folder in WSL.** Shared setup: [GUIDE](../../GUIDE.md).

```bash
ansible-playbook playbooks/baseline/main.yml -e @secrets/vault.yml --ask-vault-pass --check
ansible-playbook playbooks/baseline/main.yml -e @secrets/vault.yml --ask-vault-pass
```

Omit Vault flags for passwordless sudo or an established root login.
Add `--limit workers` or `--limit valkyrie` to select fewer hosts.

| Variable | Where / purpose |
|---|---|
| `baseline_packages` | `inventory/group_vars/all/main.yml`: packages to keep installed |
| `guest_agent_manage` | Defaults to `true`; set `false` in a host override to skip its agent tasks |
| `ansible_sudo_exe` | Ubuntu default `/usr/bin/sudo.ws`; Biteforce uses `/usr/bin/sudo` |

Check mode predicts package changes; it skips agent service inspection/start.
This job does not upgrade the whole OS.

The guest agent needs both its software **inside the VM** and the
[Proxmox agent option](../proxmox-agent/README.md). Configure both, then [verify](../verify/README.md).
