# K3s recovery — 4 October 2026 (Bangkok)

Recovered Tombstone, Whyachi, and Valkyrie over SSH. All five Kubernetes nodes are Ready, all 90 running Pods are ready, and seven Longhorn volumes are attached and healthy. Five completed Pods remain as expected.

## Findings

The original embedded etcd histories had diverged. Tombstone's key-value hash differed from the matching Whyachi/Valkyrie pair. Preserved WAL metadata also showed different terms for already committed index `44972187`: Tombstone `2366`, Valkyrie `2369`, and Whyachi `2374`. Starting the original pair elected a leader but did not advance the committed/applied index. The underlying cause of the divergent histories was not established; no kernel I/O errors or OOM kills were observed during inspection.

Valkyrie also suffered resource pressure during recovery. Its telemetry gateway used about 450 MiB resident memory, with heavy page reload activity on a roughly 2 GiB server. Stopping the already evicted gateway container allowed etcd to catch up. The gateway now runs on a worker, and its required node affinity was changed to exclude control-plane nodes in `apps/monitoring/observability/40-otel-gateway.yaml`.

## Recovery

Restored Valkyrie from `etcd-snapshot-valkyrie-1790985603`, captured on 3 October at 00:00:03 UTC / 07:00:03 Bangkok. This rolls Kubernetes and Longhorn metadata back to that snapshot; it does not restore the contents of application volume disks.

Tombstone and Whyachi rejoined with clean database directories and the original token. Tombstone initially selected SQLite because its fresh join lacked an explicitly configured token. That unintended database was preserved, then Tombstone rejoined embedded etcd successfully. Both peers now use a root-only `/etc/rancher/k3s/server-token` referenced from `/etc/rancher/k3s/config.yaml.d/99-etcd-recovery.yaml`. The temporary systemd join override was removed and normal startup was verified.

Valkyrie was temporarily cordoned and drained without deleting DaemonSets. It is uncordoned again. Longhorn orphan cleanup was checked after reconciliation; no orphans were present and the setting is back to `replica-data;instance`.

Original database, token, configuration, and journal copies remain on the servers:

| Server | Protected backup directory |
| --- | --- |
| Tombstone | `/root/k3s-diagnosis-20261003T185614Z` |
| Whyachi | `/root/k3s-diagnosis-20261003T185604Z` |
| Valkyrie | `/root/k3s-diagnosis-20261003T190103Z` |

## Verification

All three servers run embedded etcd 3.6.12 in cluster ID `18401022519079934160`. All are voting members. After the configuration restart, their applied Raft indexes were caught up to their respective committed indexes.

At common key-value revision `36161863`, all three returned hash `2761347031` with compact revision `36145767`. API `/readyz` passed on all three. Fresh snapshot saves and appended SHA-256 checks passed on every server. Status and hash evidence is saved in Tombstone's backup directory.

## Snapshot policy

All three servers load `/etc/rancher/k3s/config.yaml.d/90-etcd-snapshots.yaml`:

```yaml
etcd-snapshot-schedule-cron: "0 */6 * * *"
etcd-snapshot-retention: 5
```

The system timezone is UTC on every server. Runs occur at 00:00, 06:00, 12:00, and 18:00 UTC, corresponding to 07:00, 13:00, 19:00, and 01:00 Bangkok. Retention is a maximum of five scheduled snapshots **per server**. Peer snapshot history starts fresh after the database directories were preserved outside the active data directory.

Snapshots are stored in `/var/lib/rancher/k3s/server/db/snapshots`. Final snapshots after recovery:

| Server | Snapshot | Active scheduled snapshot count |
| --- | --- | --- |
| Tombstone | `etcd-snapshot-tombstone-1791056192` | 2 |
| Whyachi | `etcd-snapshot-whyachi-1791056191` | 2 |
| Valkyrie | `etcd-snapshot-valkyrie-1791056190` | 5 |

All final saves and pruning commands succeeded and all latest checksums validated. Incident backup copies under `/root` are retained separately from scheduled retention.

The gateway placement change is applied live and saved in the local repository, but has not been committed or pushed. Argo CD's `monitoring` Application currently has no automated sync policy; a future manual sync from the unchanged remote source could revert that placement change until the local manifest is published.

Reference: [K3s snapshot and multi-server restore documentation](https://docs.k3s.io/cli/etcd-snapshot).
