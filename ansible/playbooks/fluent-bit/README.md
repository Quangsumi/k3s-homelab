# Host log agents

**One playbook, four complete profiles.** Choose `survival`, `light`, `buffered` or `busy` in
[settings.yml](settings.yml). Default: **survival**. See [PROFILES.md](PROFILES.md) for every value and tradeoff.
Host agents collect VM/Proxmox journals. Kubernetes pod collectors keep their separate configuration.
K3s node VMs are included as machines: their OS/service journals are collected,
but this job does not read pod log files or change the pod DaemonSet.

## Apply a profile

Run from the repository's **`ansible/` folder on your Linux/WSL controller**:

```bash
ansible-playbook playbooks/fluent-bit/main.yml --limit valkyrie --check --diff \
  -e @secrets/vault.yml -e @secrets/logging-vault.yml --ask-vault-pass \
  -e fluent_bit_verify_delivery=true
ansible-playbook playbooks/fluent-bit/main.yml --limit valkyrie \
  -e @secrets/vault.yml -e @secrets/logging-vault.yml --ask-vault-pass \
  -e fluent_bit_verify_delivery=true
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

- Hosts need working SSH/sudo. Delivery checks SSH to Tantrum and use sudo Docker
  to query its Loki from the Grafana container. Include Tantrum's credentials in the host Vault as needed.
- Gateway: `192.168.63.66:443`, certificate/HTTP name `otel.tantrum.lab`.
  `fluent_bit_gateway_logs_uri: /host/v1/logs` selects host ingestion; `/v1/logs` uses the separate app receiver.
- Settings live in [inventory Fluent Bit vars](../../inventory/group_vars/all/fluent-bit.yml).
  Both the agent and connection check read the same path variable.
- The logging Vault must contain `fluent_bit_external_token` set to the contents of
  Tantrum's `apps/otel-gateway/secrets/otel-host-otlp-bearer-token`, without `Bearer `.
  Do not reuse the old stack token or the new app/remote-write tokens.
- Public CA: [tantrum-caddy.crt](../../../pki/bundles/tantrum-caddy.crt), copied from
  the new proxy's root. This job copies it to `/etc/fluent-bit/gateway-ca.pem`.
- Tokens stay out of Git. Agent configuration and backups containing tokens are root-only; template diffs are hidden.
- Journald retention stays unchanged by default. Previously installed retention settings are not removed.

This update prepares a destination change; no host agents have been changed by preparing it.
Existing installations keep `fluent_bit_install_package: false`. Keep your selected
profile to avoid changing buffering at the same time. A changed config/CA restarts
Fluent Bit when you run this job. Logs waiting in a reused disk queue may go to
the new destination; unsent RAM-buffered logs may be lost during the restart.

`fluent_bit_verify_delivery` still defaults to `false`; the commands above enable it
for this run. Checks target **Tantrum's Docker stack**, with no `kubectl` or old Loki query.
Grafana and Loki must already be running there. For the Proxmox hosts, use
`--limit endgame,deepsix`. To select every inventoried VM and Proxmox host, use
`--limit 'linux_vms:proxmox_hosts'`; inspect that list with `--list-hosts` first.

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

[New gateway paths](https://github.com/Quangsumi/tantrum-monitoring/blob/main/apps/otel-gateway/README.md) · [Labels](../../../docs/operations/log-labels.md) ·
[Recovery history](../../../docs/operations/host-logging-review-2026-10-29.md).
Pod-state [migration/cleanup](../fluent-bit-state-migration/README.md) remain separate one-time jobs.
