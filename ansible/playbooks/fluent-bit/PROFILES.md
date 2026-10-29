# Host log profiles

`settings.yml → complete profile + its own overrides → main.yml → selected hosts`

Choose by observed load. These are independent modes, not steps to complete.
**Default: `survival`.** Applies to VM/Proxmox host agents only; pod collectors are unchanged.

[Interactive mechanism page](../../../docs/visualizations/fluent-bit-mechanism.html): see the originals, DB and queues;
try RESUME/NEW, outages, restarts and rotation with synthetic logs. Open the HTML file in a browser; it works offline.

## Complete setting collections

| Setting key | `survival` | `light` | `buffered` | `busy` |
| --- | --- | --- | --- | --- |
| `cpu_quota_percent` | 5 | 5 | 5 | 10 |
| `flush_seconds` | 10 | 10 | 10 | 10 |
| `agent_diagnostic_log_level` | error | error | error | error |
| `rate_records` | 20 | 100 | 100 | 200 |
| `rate_bytes` | 32K | 128K | 128K | 256K |
| `memory_buffer` | 1M | 2M | 2M | 4M |
| `save_positions` | false | false | true | true |
| `disk_buffering` | false | false | true | true |
| `queue_limit` | 64M (unused) | 64M (unused) | 64M | 64M |
| `storage_max_chunks_up` | 2 (unused) | 2 (unused) | 2 | 4 |
| `storage_backlog_memory` | 1M (unused) | 1M (unused) | 1M | 2M |
| `journal_max_entries` | 20 | 50 | 50 | 100 |
| `tail_batch_size` | 32K | 32K | 32K | 64K |

- **survival:** least agent work; no agent queue/database writes. Can fall behind during noisy periods.
- **light:** more collection capacity, still RAM only. Suitable when delivery is reliable and restart gaps are acceptable.
- **buffered:** saved reading positions plus a small disk queue. Candidate for healthy storage.
- **busy:** higher CPU/collection budget for a noisy machine. Measure disk waits before keeping it.

CPU percentages are of **one core**. Rates apply **per input, per second**, to log data, not physical disk speed.
`memory_buffer` is per input in RAM mode, not total agent memory. Filesystem mode instead uses the chunk count;
chunks average about 2 MB and this is not a hard RAM cap. `storage_backlog_memory` limits old queue data brought into RAM.
`journal_max_entries` limits one reading round. `tail_batch_size` limits one existing/new file-read batch.
`queue_limit` is a logical queue cap; oldest chunks drop at the cap, and database/filesystem overhead is extra.

All profiles use low process/disk priority, unlimited delivery retries and a localhost monitoring port of 2021.
Saved databases use `DB.Sync Normal`; disk queues use `storage.sync normal` with checksums. `Full` is not offered.
Normal sync reduces forced writes, with a larger recent-data loss window on a sudden power loss.
RAM modes can lose unsent data on restart or miss source logs that rotate while collection is paused.
Existing logs in Loki and the installed journald retention policy are not changed.

**`agent_diagnostic_log_level` controls Fluent Bit's own messages only.** It does not filter host/application logs.
All source severities are still collected. `error` avoids a rate-limit warning every second; use a profile-specific
`warn` or `info` override temporarily to investigate the agent. Grafana's `unknown` means the source severity
was not identified; it does not mean non-error logs were excluded.

## Choose and apply

1. Edit `fluent_bit_profile` in [settings.yml](settings.yml).
2. Optionally edit **only that profile's** entry under `fluent_bit_profile_overrides`.
3. Run from the repository's **`ansible/` folder on Linux/WSL**:

```bash
ansible-playbook playbooks/fluent-bit/main.yml --limit tombstone \
  -e @secrets/vault.yml -e @secrets/logging-vault.yml --ask-vault-pass
```

This command changes the selected host. Add `--check --diff` for preview; the token/config diff is hidden.
Profiles are complete. Switching profile rebuilds every managed setting; overrides from other profiles do not carry over.
The playbook never merges settings from the currently installed configuration. Invalid/incomplete profiles stop before changes.

Default behavior: configure the installed agent, verify a fresh message in Loki, and print 30-second before/after load samples.
An unavailable baseline is reported; high load does not block selecting survival. No stages, load thresholds or NEXT prompts.
Only Fluent Bit restarts when its settings change. Several selected hosts are still processed one at a time.
Watch Host Logs, Log Delivery, CPU and disk waits during normal and busy periods; choose the next profile/host yourself.

- New host: set `fluent_bit_install_package: true`; existing hosts default to no package work.
- Urgent recovery with the gateway down: set `fluent_bit_verify_delivery: false`. Delivery is then explicitly unverified.
- Skip automatic samples: set `fluent_bit_observe_load: false`. You can observe your own dashboards instead.
- Different Vault passwords: use `--vault-id hosts@prompt --vault-id logging@prompt` instead of `--ask-vault-pass`.

## Existing state: no silent replay or deletion

All profiles use the **existing** folder. No `permanent/` subfolder:

```text
/var/lib/fluent-bit/host/
├── journal.db   ← bookmark: remembers where reading stopped
└── queue/      ← actual log messages waiting to be sent
```

1. **Switch to RAM:** these disk files stay where they are. The agent stops using them.
2. **Switch back to disk:** the playbook asks what to do with an unused bookmark. It changes nothing until you answer.

Example: the bookmark says **100**, but RAM mode already sent **101–200**:

| Your answer | What happens |
| --- | --- |
| **RESUME** | Read after 100 again. Logs 101–200 may appear twice in Grafana. |
| **NEW** | Delete the unused bookmark without backup. Start from the newest source entries. If 200 is still the latest, collection continues with 201. Unread older entries are skipped. |

**The queue is separate. Both answers keep it in place.** When disk buffering resumes, its unsent messages are sent,
even with NEW. NEW resets the reading bookmark; it does not empty the queue or erase logs already stored in Loki.
NEW removes only unused position databases and their SQLite sidecar files, with no backup folder or undo copy.
It never deletes the source journal, source log files or queue. Active position databases are never reset.

- **Queue but no bookmark?** Type RESUME to confirm sending the waiting messages. No bookmark needs resetting.
- **Already using disk mode?** Keep the active bookmark/queue. No repeat question.
- **No files yet?** Start with new entries. No question.
- **Wrong answer or cancelled?** Stop without changing settings or files.
- **Existing queue larger than the chosen cap?** Stop before applying it, to avoid dropping waiting logs.
  Set an explicit larger `queue_limit` override (128M, 256M, 512M or 1024M) to retain/drain it, then reduce the cap afterward.
  This changes queue capacity, not the collection rate or CPU limit. File-size checks include overhead and are conservative.

Keep `fluent_bit_position_action: ask` in the settings file. For one unattended run, deliberately add
`-e fluent_bit_position_action=resume` or `-e fluent_bit_position_action=new_entries`.
That choice lasts for that command only. NEW is never applied to an active bookmark, and does not reset it on every run.
`--check` reports the needed choice and moves nothing. All profiles use the same playbook.

References: [journal positions](https://docs.fluentbit.io/manual/data-pipeline/inputs/systemd.md),
[buffering, rate gates and queue limits](https://docs.fluentbit.io/manual/data-pipeline/buffering.md).
