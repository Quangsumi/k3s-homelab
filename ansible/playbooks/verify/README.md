# Verify

Read addresses, routes, `/etc/resolv.conf` and the guest-agent service state.
No configuration changes; includes Hydra.

From the `ansible` folder in WSL:

```bash
ansible-playbook playbooks/verify/main.yml
```

Add `--limit valkyrie` to inspect one host. SSH must already work.

| Report | What to check |
|---|---|
| Addresses | Expected guest IP is present |
| Routes | Expected default gateway |
| Resolver | Expected configuration; a local stub address may appear |
| Agent | Guest-agent service is running |

This reports observations, rather than asserting everything is healthy.
For Ubuntu DNS, also check `resolvectl status` and resolve a known internal name.
Confirm Proxmox can communicate with the guest agent separately.
Shared connection setup: [GUIDE](../../GUIDE.md).
