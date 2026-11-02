# Verify K3s metrics on Tantrum

## 1. Inspect the Agent's actual scrape targets

After rollout, these account checks should return `yes`:

```bash
kubectl auth can-i list nodes --as=system:serviceaccount:monitoring:prometheus-agent
kubectl auth can-i list endpointslices.discovery.k8s.io --all-namespaces --as=system:serviceaccount:monitoring:prometheus-agent
kubectl auth can-i get nodes --subresource=proxy --as=system:serviceaccount:monitoring:prometheus-agent
kubectl auth can-i get /metrics --as=system:serviceaccount:monitoring:prometheus-agent
```

On your Kubernetes controller:

```bash
kubectl -n monitoring port-forward statefulset/prometheus-agent 9095:9095
```

Open `http://localhost:9095/targets`. API/scheduler/controller/etcd jobs should each
have **three UP targets**; kubelet/cAdvisor should each have **five**.
Keep this terminal open for the browser session; stop port-forward with Ctrl+C.

**Tantrum's `/targets` page will not list these remote scrapes.** Its receiver
stores the Agent's samples; target discovery/status is on the Agent. The queries
below show forwarded `up` samples in central Prometheus.

## 2. Verify received data in Tantrum Prometheus or Grafana Explore

Use the Tantrum Prometheus data source, not the old K3s server.

```promql
count by (job) (up{cluster="k3s-homelab"} == 1)
up{cluster="k3s-homelab"} == 0
```

The second query should be empty once all jobs are reachable. Expected core counts:

| Job | UP count |
| --- | --- |
| `kubernetes-apiserver` | 3 |
| `kubernetes-scheduler` | 3 |
| `kubernetes-controller-manager` | 3 |
| `kubernetes-etcd` | 3 |
| `kubernetes-kubelet` | 5 |
| `kubernetes-cadvisor` | 5 |
| `kube-state-metrics`, `kube-state-metrics-self`, `prometheus-agent` | 1 each |
| `node-exporter` with the cluster label | 5; still direct scraping |

Baseline for other jobs before this rollout: Argo CD 5; cert-manager 3; CoreDNS 2;
External Secrets 3; Fluent Bit 5; kube-vip 3; LiteLLM 1; PostgreSQL exporter 1;
Longhorn CSI 8; Longhorn manager 2; Tailscale operator 1; Traefik 3; trust-manager 1.
These counts change with replicas/components: compare against current discovery,
not an assumption that every cluster always has this many pods.

**UP is not proof of useful metric families.** Run each query separately:

```promql
kube_pod_info{job="kube-state-metrics", cluster="k3s-homelab"}
container_cpu_usage_seconds_total{job="kubernetes-cadvisor", cluster="k3s-homelab", container!=""}
kubelet_running_pods{job="kubernetes-kubelet", cluster="k3s-homelab"}
apiserver_request_total{job="kubernetes-apiserver", cluster="k3s-homelab"}
scheduler_pending_pods{job="kubernetes-scheduler", cluster="k3s-homelab"}
running_managed_controllers{job="kubernetes-controller-manager", cluster="k3s-homelab"}
etcd_server_has_leader{job="kubernetes-etcd", cluster="k3s-homelab"}
```

Require data for each applicable family. Etcd `has_leader` must be **1 on all three**.
Some scheduler/controller families appear only on the elected leader or after
activity. Shared K3s workqueue metrics are grouped with controller-manager; the job
name does not mean a separate controller-manager process exists.

## 3. Check sending and capacity

```promql
prometheus_remote_storage_samples_pending{job="prometheus-agent", cluster="k3s-homelab"}
rate(prometheus_remote_storage_samples_failed_total{job="prometheus-agent", cluster="k3s-homelab"}[5m])
time() - max(timestamp(up{job="prometheus-agent", cluster="k3s-homelab"}))
```

Pending samples should drain or remain low, failed samples should not keep rising,
and self-metrics should stay fresh. Check Agent `/metrics` through the port-forward
and its logs too: a total sending failure also prevents these diagnostics reaching
Tantrum. `/-/ready` is only process readiness, not delivery.

```bash
kubectl -n monitoring get pod prometheus-agent-0
kubectl -n monitoring top pod prometheus-agent-0
kubectl -n monitoring logs prometheus-agent-0 -c prometheus-agent --since=10m
```

On Tantrum, from the Docker repo root:

```bash
sudo docker compose stats --no-stream prometheus
sudo docker compose logs --since=10m prometheus proxy
```

Check restarts, queue/disk growth and central Prometheus memory after several
scrape intervals and during normal app activity. There is no fixed safe series
count implied by its 1 GiB memory ceiling.

## 4. Diagnose by failure

| Symptom | Check |
| --- | --- |
| Pod cannot mount config | CA ConfigMap, both Secrets and ExternalSecret Ready conditions |
| Config init fails | `logs ... -c validate-config`; projected file names/keys |
| Agent Pending | PVC binding, Longhorn capacity and scheduling resources |
| Discovery or scrapes return 403 | Own ServiceAccount/ClusterRoleBinding, `/metrics` and node-proxy permissions |
| LiteLLM/Postgres/Longhorn time out | Their Argo apps must sync the Agent network-policy allowance |
| Etcd connection refused | Enable the host flag and restart that member; verify private-IP listener |
| Etcd timeout | Host firewall/pod route to port 2381; no bearer token is used on this HTTP metrics port |
| Remote write 401 | Infisical value must equal Caddy's existing Prometheus write token |
| Remote write certificate error | Tantrum root and `metrics-write.tantrum.lab` name; never disable verification |
| Fresh Agent targets, stale central data | Agent sending logs/queue, hostAlias IP, Caddy route and receiver |

## 5. Cutover and rollback

Only after target counts, actual metric families and sending pass, retire the old
K3s server in a separate reviewed change: remove `prometheus` and
`prometheus-oauth2-proxy` from the monitoring Kustomization, then sync with Prune.
The Agent has its own account/config/disk and owns the existing LiteLLM
ExternalSecret. Keep kube-state-metrics, Fluent Bit, trust-manager's CA and the Agent.
Review any remaining consumers of the old server before pruning its Service.
Leave `prometheus-data-prometheus-0` alone; delete its old history only as a separate
manual decision. This PR does not retire that server or any other backend.

If Agent verification fails, the old server still works. Temporarily stop sending:

```bash
kubectl -n monitoring scale statefulset/prometheus-agent --replicas=0
```

For a durable rollback, revert this Agent PR and sync the affected apps. Argo CD
self-heal may undo a manual scale-down. Keep `wal-prometheus-agent-0`; it is retained
for recovery. To undo the host metrics exposure, remove only your new drop-in (or
restore its original contents), restart servers one at a time and repeat etcd health
checks. That host setting is independent of GitOps.

## Read-only preparation record

Focused metrics assessment on **2026-11-02, about 23:05–23:18 Asia/Bangkok**.
This is a point-in-time endpoint/consistency result, not a full infrastructure-health
assessment or evidence that the new Agent has been deployed. The temporary etcd
collector/config were removed; private keys stayed on the server.

| Check ID | Target / result | Status / comment |
| --- | --- | --- |
| C01 | VM 100/101 on Endgame; VM 111 on Deep Six; all five expected node addresses/roles discovered | PASS; guest-agent checks used authorized Proxmox access |
| C09 | All three servers report K3s `v1.36.2+k3s1`; loopback 2381 works on each | PASS for endpoint/version scope; service/journal history not assessed |
| C10 | Etcd `3.6.12`; three endpoints healthy, same leader/term 597, no sampled applied-index backlog | PASS at sample time |
| C11 | Three expected voters, same cluster ID, healthy count 3, quorum size 2 | PASS; membership matches inventory |
| C12 | Alarm query succeeded with an empty list on all three | PASS; no alarms at sample time |
| C13 | All three hashes `400645490` at revision `53145809`, common compaction revision `53142867` | PASS; comparable sample, collector exit 0 |
| C14 | Authenticated direct readiness on all three servers and VIP readiness return `ok` | PASS; scheduler/controller families present on direct 6443 endpoints |
| C15 | Biteforce, Huge, Minotaur, Tombstone and Whyachi Ready | PASS for readiness; pressure trends not assessed |
| C19 | All existing Prometheus scrape targets UP; central etcd collection unavailable on node-IP 2381 | WARN; localhost-only metrics need the manual host flag before new etcd jobs can be UP |
| C02, C03, C04, C05, C06, C07, C08, C16, C17, C18 | Host resets/quorum/HA/network/storage/pressure/filesystems/snapshots/failure resilience/NFS | N/A; outside this metrics deployment request |

No infrastructure settings were changed during discovery. Post-rollout sending,
new Agent credentials/permissions and sustained capacity checks remain operator
verification steps above.

Prometheus v3.15.1 accepted the full Agent config with isolated placeholder credentials;
the live API accepted all new resources/policy changes in strict server dry-run.
Live metric-name checks confirmed separate filters on all three servers, and
kubelet/cAdvisor node-proxy checks passed on all five nodes. The Agent remains undeployed.

The initial Kubernetes Service-proxy probe of old Prometheus returned 502. Querying
its API from inside its pod succeeded and showed every current target UP; the
Service-proxy result was not treated as a scrape failure.
