# Host log agents

**One playbook, four complete profiles.** Choose `survival`, `light`, `buffered` or `busy` in
[settings.yml](settings.yml). Default: **survival**. See [PROFILES.md](PROFILES.md) for every value and tradeoff.
Host agents collect VM/Proxmox journals. Kubernetes pod collectors keep their separate configuration.

## Apply a profile

Run from the repository's **`ansible/` folder on your Linux/WSL controller**:

```bash
ansible-playbook playbooks/fluent-bit/main.yml --limit tombstone \
  -e @secrets/vault.yml -e @secrets/logging-vault.yml --ask-vault-pass
```

1. Choose the profile and any changes under **that profile's** overrides in `settings.yml`.
2. Select one host with `--limit`. The same command applies survival or any other profile.
3. Review the before/after measurements and Grafana. Choose another profile or host when ready.

No stages or automatic load thresholds. Several selected hosts are processed one at a time; failures stop the run.
Existing hosts skip package installation. For a new host, set `fluent_bit_install_package: true`.
Fluent Bit restarts only when configuration changes. No VM/K3s restart is performed.

- Preview: add `--check --diff`. Connection checks still run; new load/delivery cannot be proved in preview.
- Different Vault passwords: use `--vault-id hosts@prompt --vault-id logging@prompt` instead of `--ask-vault-pass`.
- For gateway outages, disable `fluent_bit_verify_delivery` explicitly; the run then makes no delivery claim.
- Before/after samples are optional: `fluent_bit_observe_load`. They report load without choosing a mode for you.

## Connections and secrets

- Hosts need working SSH/sudo. Tombstone runs `kubectl` and queries Loki through Grafana for delivery checks.
- Gateway: `192.168.63.69:31419`, TLS certificate name `otel-otlp.lab`. Deploy that endpoint before enabling verification.
- The logging Vault contains `fluent_bit_external_token: 'YOUR_EXISTING_INFISICAL_TOKEN'`.
  Use Infisical `/otel-gateway/EXTERNAL_BEARER_TOKEN`, without `Bearer `. [Vault example](../../secrets/logging-vault.example.yml).
- Tokens stay out of Git. Agent configuration and backups containing tokens are root-only; template diffs are hidden.
- Journald retention stays unchanged by default. Previously installed retention settings are not removed.

## Profile changes and saved state

Every profile is complete. The collection is rebuilt from the selected profile and its own overrides, never the previous profile.
All profiles use `/var/lib/fluent-bit/host/`: `journal.db` remembers where reading stopped; `queue/` holds unsent logs.
Returning from RAM asks **RESUME** (use the old bookmark; duplicates possible) or **NEW** (delete the unused bookmark without backup; read new entries).
Both keep the queue. Its waiting messages are still sent. No extra state folder is created.
[Line-number example and unattended choices](PROFILES.md#existing-state-no-silent-replay-or-deletion).
RAM modes can lose unsent logs on restart. Positions alone do not preserve unsent RAM logs.
`agent_diagnostic_log_level` affects Fluent Bit's own messages only; all host/application severities are collected.

## View logs

Grafana → **Dashboards → Logs**:

- **Host Logs:** choose a machine and system service.
- **Pod Logs:** choose a namespace, application and pod.
- **Log Delivery:** heartbeat age under five minutes indicates current host delivery; a backlog can make it red.

[Gateway paths](../../../docs/operations/otel-gateway-access.md) · [Labels](../../../docs/operations/log-labels.md) ·
[Recovery history](../../../docs/operations/host-logging-review-2026-10-29.md).
Pod-state [migration/cleanup](../fluent-bit-state-migration/README.md) remain separate one-time jobs.
