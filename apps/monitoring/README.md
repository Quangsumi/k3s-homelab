# Monitoring

One folder per application. `kustomization.yaml` remains Argo CD's entry point.

| Folder | Contents |
|---|---|
| `grafana/` | UI, data sources, dashboards and network rules |
| `prometheus/` | Server, scrape configuration, access rules and RBAC |
| `prometheus-oauth2-proxy/` | Prometheus login proxy and ingress |
| `fluent-bit/` | Pod collector, four editable profile files and manual state-maintenance Jobs |
| `otel-gateway/` | Log/metric/trace receiver, routes, RBAC and network rules |
| `loki/` | Log storage |
| `jaeger/` | Trace storage and UI |
| `aspire-dashboard/` | Aspire UI and receiver |
| `node-exporter/` | Node operating-system metrics |
| `kube-state-metrics/` | Kubernetes object metrics |
| `shared/` | Namespace, shared storage class and cross-application metrics rule |
| `otel-agent/` | Retained older collector manifest; **not deployed** |

Each active application has its own `kustomization.yaml`. Resource names and namespace remain unchanged.
The earlier discussion is preserved in [architecture-notes.md](architecture-notes.md).

For pod collector settings and one-node rollout, use
[the K3s profile guide](fluent-bit/README.md).
Host-agent settings remain in [their own playbook](../../ansible/playbooks/fluent-bit/README.md).

Local build checks, from the repository root:

```bash
kubectl kustomize apps/monitoring
kubectl kustomize apps/monitoring/fluent-bit
```

These commands render YAML only. They do not apply it.
