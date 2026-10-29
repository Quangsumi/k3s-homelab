# Host log agent

Collects VM/Proxmox journals and sends them to Loki. Pod logs use the separate Kubernetes collector.
Completes **install → configure → verify delivery to Loki** on one host before moving to the next. Stops on failure.

## Before running

- Deploy the reviewed gateway LAN endpoint first: `192.168.63.69:31419`, TLS name `otel-otlp.lab`.
- Hosts need working SSH/sudo. Tombstone needs working `kubectl` access to the Grafana pod for delivery checks.
- Load your SSH/sudo Vault and logging Vault. The logging Vault must contain:

```yaml
fluent_bit_external_token: 'YOUR_EXISTING_INFISICAL_TOKEN'
```

Use the value from Infisical `/otel-gateway/EXTERNAL_BEARER_TOKEN`, without `Bearer `.
Keep real tokens out of Git. [Example](../../secrets/logging-vault.example.yml).

## Run

From the repository's **`ansible/` folder on your Linux/WSL controller**:

```bash
ansible-playbook playbooks/fluent-bit/main.yml \
  --limit 'linux_vms:proxmox_hosts' \
  -e @secrets/vault.yml \
  -e @secrets/logging-vault.yml \
  --ask-vault-pass
```

- Test Tombstone first: replace the limit with `tombstone`.
- Skip Tombstone afterward: use `'linux_vms:proxmox_hosts:!tombstone'`.
- Preview: add `--check --diff`. Connection checks still run; a fresh installation cannot be fully simulated.
- Different Vault passwords: replace `--ask-vault-pass` with `--vault-id hosts@prompt --vault-id logging@prompt`.
- Run the whole playbook; do not use `--start-at-task`.

Success ends with **Verified HOST -> Fluent Bit -> gateway -> Loki** for each host.

## Settings that matter

Defaults: [fluent-bit.yml](../../inventory/group_vars/all/fluent-bit.yml).

- **Journal retention:** managed by default: 256 MB / up to 7 days. May restart journald. Set `fluent_bit_manage_journal: false` to skip policy changes; this does not undo an earlier policy change.
- **Saved positions and queue:** `/var/lib/fluent-bit/host/`. Queue cap: 512 MB; oldest queued data is dropped at the cap.
- **Token:** stored in root-only agent configuration. Protected backups also contain tokens.
- **Heartbeat:** one test log per minute proves delivery, even when the host is quiet.

## View logs

Grafana → **Dashboards → Logs** after deploying the dashboard configuration:

- **Host Logs:** select a machine and system service.
- **Pod Logs:** select a namespace, application and pod.
- **Log Delivery:** green = heartbeat received within 5 minutes; red = missing.

[Gateway connection paths](../../../docs/operations/otel-gateway-access.md) · [Label explanation](../../../docs/operations/log-labels.md) · [Review/rollout notes](../../../docs/operations/host-logging-review-2026-10-29.md)

Pod-state [migration and cleanup](../fluent-bit-state-migration/README.md) remain separate, one-time jobs.
