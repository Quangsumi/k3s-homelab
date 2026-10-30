# Fluent Bit pod logs

**Kubernetes manifests only. Nothing has been applied.** Host agents keep their separate Ansible playbook.

```text
profiles/<mode>/fluent-bit.conf → ConfigMap → one DaemonSet → gateway → Loki
manifest.yaml: node filename → profile key
```

## Settings and profile selection

Each file under `profiles/` is a **complete, directly editable configuration**. No inherited overrides,
renderer, Python selector or generated node JSON. Kustomize loads the files into a ConfigMap.

| Per node | survival | light | buffered | busy |
|---|---:|---:|---:|---:|
| Records/second | 20 | 100 | 100 | 200 |
| Log bytes/second | 32K | 128K | 128K | 256K |
| Waiting messages | RAM | RAM | Disk + RAM | Disk + RAM |
| Saved bookmarks | No | No | Yes | Yes |
| RAM input buffer | 1M | 2M | Chunk-based | Chunk-based |
| Disk queue cap | Unused | Unused | 64M | 64M |

All send every 10 seconds. Rates cover **all container logs on one node combined**;
they are not physical disk-speed limits. CPU stays at 50m (5% of one core), total memory at 96Mi.
Disk profiles use Normal synchronization and 2/4 in-memory chunks, averaging roughly 2 MB each.
Queue cap is logical, with additional filesystem overhead; oldest waiting chunks drop at the cap.
`Log_Level` controls Fluent Bit's own messages, **not which application severities are collected**.

Choose a node's profile in `manifest.yaml`, under `volumes → configMap → items`:

```yaml
- key: buffered.conf   # The profile to use
  path: whyachi.conf   # Kubernetes node name + .conf
```

All five nodes currently select `survival.conf`. Kubernetes supplies `NODE_NAME`;
the collector opens `/fluent-bit/profiles/$(NODE_NAME).conf`. Unlisted nodes have no matching file and fail visibly.

`OnDelete` prevents configuration publication from restarting every collector.
Immutable, named ConfigMap snapshots keep existing pods on their current settings.
A recreated pod uses its node's latest published assignment. Change only the node you intend to trial.

## Review locally — repository root

```bash
kubectl kustomize apps/monitoring/fluent-bit
```

This prints YAML only. No Ansible or external generation step is needed.

## Roll out ONE node later — a terminal with kubectl and this checkout

Example: Whyachi. Keep monitoring's Argo CD automatic sync paused during a local trial.
**Do not prune old ConfigMaps until their collector pods have been replaced.**

1. Edit Whyachi's mapping and, if needed, its selected profile file. Pause Whyachi **before publishing**:

   ```bash
   kubectl label node whyachi logging.homelab/fluent-bit-paused=true --overwrite
   kubectl apply -k apps/monitoring/fluent-bit
   kubectl -n monitoring wait --for=delete pods -l app.kubernetes.io/name=fluent-bit --field-selector=spec.nodeName=whyachi --timeout=120s
   ```

   These commands change the cluster: publish the native resources and stop only Whyachi's collector.
   On first adoption, the pause takes effect when the new DaemonSet is published. K3s and host agents keep running.

2. **Returning to disk mode or lowering its queue cap:** edit the hostname and cap in
   `maintenance/inspect-state.yaml`, then inspect:

   ```bash
   kubectl create -f apps/monitoring/fluent-bit/maintenance/inspect-state.yaml
   kubectl -n monitoring wait --for=condition=complete job/fluent-bit-state-inspect --timeout=180s
   kubectl -n monitoring logs job/fluent-bit-state-inspect -c inspect
   ```

   **RESUME:** keep bookmarks and queue; old positions may repeat logs already sent in RAM.
   **NEW:** after setting its hostname/cap, run:

   ```bash
   kubectl create -f apps/monitoring/fluent-bit/maintenance/new-entries.yaml
   kubectl -n monitoring wait --for=condition=complete job/fluent-bit-new-entries --timeout=180s
   ```

   This deletes only unused bookmarks, without backup.
   Both keep and later send queued messages. If only a queue exists, choose RESUME.
   If neither exists, start with new entries. If inspection fails, keep paused and fix the reported issue.

3. After any maintenance Job has completed, resume Whyachi:

   ```bash
   kubectl label node whyachi logging.homelab/fluent-bit-paused-
   kubectl -n monitoring get pods -w -l app.kubernetes.io/name=fluent-bit --field-selector=spec.nodeName=whyachi
   ```

   Watch for `1/1` Ready, then press Ctrl+C. Check Pod Logs in Grafana and node I/O before choosing another node.
   Readiness alone does not prove delivery; confirm a newly emitted application message in Loki.

Maintenance Jobs are **not included in Kustomize** and never run on ordinary startup.
They require the pause label and wait for the old collector to exit. Keep that label until the Job completes.
`create` deliberately refuses to rerun a completed Job with the same name; delete the finished Job before an intentional repeat.
Jobs expire after ten minutes. A normal collector restart never deletes bookmarks.

**State choices and cap checks are explicit operator steps**, not automatic startup checks.
Do not publish a RAM-to-disk change for an unpaused node: an incidental pod recreation could resume its old state.

State stays at `/var/lib/fluent-bit/pods/flb_kube.db` and `/var/lib/fluent-bit/pods/queue/` on each node.
RAM mode leaves those files unused; disk-to-disk changes keep them active. No markers or backup folders are added.
K3s still owns original log files and rotation. RAM restarts may lose unsent messages; falling behind rotation may lose unread originals.

References: [native argument expansion](https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/),
[ConfigMap file mapping](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/),
[DaemonSets](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/).
