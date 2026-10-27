# Discover

Read OS/version, default IP/gateway, interfaces, Netplan filenames and network services.
No configuration changes; includes Hydra.

From the `ansible` folder in WSL:

```bash
ansible-playbook playbooks/discover/main.yml
```

Add `--limit valkyrie` to inspect one host. SSH must already work.
This job lists files; it does not establish which tool currently owns their contents.
Shared connection setup: [GUIDE](../../GUIDE.md).
