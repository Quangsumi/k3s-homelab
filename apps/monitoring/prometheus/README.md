# Prometheus configuration

**Local changes only. Nothing has been applied.**

`prometheus.yml` contains the shared settings. Files in `scrapes/` contain the
jobs, grouped by component. Edit those ordinary YAML files; do not paste them
back into the Kubernetes manifest.

| File | What Prometheus collects |
|---|---|
| `applications.yml` | LiteLLM and PostgreSQL exporter |
| `kubernetes.yml` | Node Exporter, kubelet, cAdvisor, API servers and kube-state-metrics |
| `observability.yml` | Prometheus, Grafana, Fluent Bit, Loki, Jaeger and OTel gateway |
| `network.yml` | Traefik, CoreDNS, kube-vip and Tailscale operator |
| `argocd.yml` | Argo CD's five enabled metrics endpoints |
| `certificates.yml` | cert-manager, cainjector, webhook and trust-manager |
| `external-secrets.yml` | External Secrets controller, cert controller and webhook |
| `storage.yml` | Longhorn managers and CSI controllers |

Prometheus 3.5.4 supports `scrape_config_files`, which loads these files directly.
Kustomize packages them into two ConfigMaps: one for shared settings and one for
the job files. Their generated name hashes make a config change trigger a pod
rollout after deployment. There is no extra generator script or reload sidecar.
The projected volume puts config files and the existing LiteLLM token in the
same read-only directory; the token is still supplied by the existing Secret.

All 13 previous job names, their intervals, authentication and kubelet metric
filter are retained. Node Exporter and Fluent Bit discovery now use Kubernetes
EndpointSlices instead of the deprecated Endpoints API. New jobs use 30-second
intervals and explicit namespace/component/port filters. Pod IPs are discovered
automatically. Labels identify namespace, pod, node, component and cluster.

## Coverage and limits

The new jobs cover the 24 previously uncollected endpoints. Further read-only
checks also confirmed Grafana, two Longhorn managers, the Tailscale operator,
three API servers and kube-state-metrics' own monitoring port. Those are included
too. Current addresses/replica counts are discovery results, not hardcoded IPs.

Grafana and Longhorn managers expose metrics on ports also used for their APIs.
The local network-policy changes permit those ports only from the Prometheus
pods. Kubernetes NetworkPolicy cannot restrict an HTTP path to `/metrics`.
The Longhorn rule belongs to `infrastructure/longhorn/40-network-policies.yaml`;
both the monitoring and Longhorn changes are needed during an approved rollout.

Not added as working targets:

* Dex: its declared metrics port is not listening.
* Longhorn global manager: its health port returns 404 for `/metrics`.
* metrics-server: its serving certificate has no trusted CA configured in its
  APIService; no insecure TLS scrape is introduced by this work.
* OAuth2 proxies: no enabled metrics listener was found in their settings.
* Other apps without a confirmed exporter, including the currently deployed
  NormalAssNote image. Its future OTLP metrics will use the existing gateway job.

## Check and deploy later

From the repository root, render without applying:

```bash
kubectl kustomize apps/monitoring
kubectl kustomize infrastructure/longhorn
```

From this `prometheus/` folder, with Prometheus 3.5.4's `promtool` installed:

```bash
promtool check config --syntax-only prometheus.yml
```

That checks configuration without requiring copies of the live token/CA files.
It does not prove live scrape success. After an approved rollout, check
Prometheus Targets and Grafana, then measure memory and stored series. The
existing memory limit and 5 GiB storage/retention settings are unchanged.

## Validation — 2026-10-28

* Prometheus 3.5.4 `promtool` accepted the configuration, including a full check
  of a local copy with dummy credential files and the public Kubernetes CA.
* All 13 original job definitions were compared with the previous config.
  The only intended change to those jobs is EndpointSlice discovery for Node
  Exporter and Fluent Bit.
* Discovery rules matched 63 endpoints across 25 jobs in the current Kubernetes
  metadata. No job matched zero endpoints and no duplicate target URLs were
  found within a job. This checks selection, not live scrape health.
* Both monitoring and Longhorn Kustomizations render. The Prometheus volume
  references the generated ConfigMap names and includes all eight job files.

No configuration has been applied, no service restarted, and no commit/push made.

Reference: [Prometheus scrape configuration files](https://prometheus.io/docs/prometheus/latest/configuration/configuration/).
