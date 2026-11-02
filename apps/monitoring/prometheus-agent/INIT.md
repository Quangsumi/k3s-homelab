# Initialize and roll out the K3s Agent

Run repository commands from the **homelab repo root** on your Kubernetes controller.
Keep the old K3s Prometheus and its PVC until [verification](VERIFY.md) passes.

## 1. Supply the existing destination credential and CA

| Owner | Required value |
| --- | --- |
| Tantrum Caddy | Existing `PROMETHEUS_REMOTE_WRITE_BEARER_TOKEN` in its proxy environment |
| Infisical | Set `/prometheus/REMOTE_WRITE_BEARER_TOKEN` to that same raw value, without `Bearer ` |
| Kubernetes | External Secrets creates `prometheus-agent-remote-write-token`; no plaintext token in Git |
| trust-manager | Existing `tantrum-caddy-trust-bundle` ConfigMap in `monitoring`, key `tantrum-caddy.crt` |

Do not generate a different token for the Agent or change the OTel tokens.
The existing LiteLLM Infisical credential is reused unchanged.

```bash
kubectl -n monitoring get configmap tantrum-caddy-trust-bundle
kubectl get clustersecretstore infisical
```

If the CA is missing, use the existing [PKI distribution flow](../../../pki/README.md)
before starting the Agent. The pod does not create its own CA copy.

## 2. Enable etcd metrics on the three servers

Discovery found 2381 listening only on localhost. Scheduler/controller-manager
metrics already exist on authenticated 6443; **no bind-address changes for those**.

Perform this step manually on **Tombstone, then Whyachi, then Biteforce**, finishing
all checks on one server before changing the next. No worker changes are needed.
The three-server etcd cluster must retain at least two healthy voters.

Before each restart, run on a control-plane server:

```bash
sudo /usr/local/bin/etcdctl --endpoints=https://192.168.63.20:2379,https://192.168.63.21:2379,https://192.168.63.67:2379 \
  --cacert=/var/lib/rancher/k3s/server/tls/etcd/server-ca.crt \
  --cert=/var/lib/rancher/k3s/server/tls/etcd/client.crt \
  --key=/var/lib/rancher/k3s/server/tls/etcd/client.key endpoint health
```

Require all three to be healthy before proceeding. Keep all etcd keys on the server.
Review existing config/drop-ins for an override of this setting, then create/edit:

```bash
sudo install -d -m 755 /etc/rancher/k3s/config.yaml.d
sudoedit /etc/rancher/k3s/config.yaml.d/95-etcd-metrics.yaml
```

File content:

```yaml
etcd-expose-metrics: true
```

Restart **only this server**, then check it before the next server:

```bash
sudo systemctl restart k3s
sudo systemctl is-active k3s
sudo k3s kubectl --request-timeout=15s get --raw=/readyz
sudo k3s kubectl get nodes
sudo ss -ltnp 'sport = :2381'
```

Repeat the three-endpoint health command. Require API readiness, Ready nodes and
all three healthy etcd endpoints. If a check fails, stop the sequence and inspect
that server; do not restart another voter.

The flag adds an **unauthenticated HTTP metrics listener on the node's private IP**.
Allow access from cluster pods (`10.42.0.0/16` in this lab), or their node source
addresses if the network translates pod traffic; keep it off public routes.
No change to etcd client/peer ports 2379/2380, TLS or membership is needed.
If host firewalls restrict pod traffic, adjust that policy manually before verifying.

## 3. Review and sync GitOps

Review rendered resources locally:

```bash
kubectl kustomize apps/monitoring/prometheus-agent
kubectl kustomize apps/monitoring
kubectl apply --dry-run=server -k apps/monitoring/prometheus-agent
```

The last command validates against the cluster API without creating resources.

After merging the homelab PR, review/sync **litellm, postgres and longhorn** in Argo CD
to admit the new Agent to their existing metrics endpoints. Then sync **monitoring**.
The new pod uses its own labels/account/Service/PVC; the old Prometheus Service
continues selecting only the old server.

CLI example, after reviewing each app's diff:

```bash
argocd app sync litellm
argocd app sync postgres
argocd app sync longhorn
argocd app sync monitoring
```

This sync adds the Agent; do not prune or disable the old server yet. The existing
LiteLLM ExternalSecret stays in `../prometheus/manifest.yaml`; both collectors use
its generated Secret. Keep that definition when later stopping the old server.

## 4. Wait for prerequisites and the pod

```bash
kubectl -n monitoring wait --for=condition=Ready externalsecret/prometheus-agent-remote-write-credentials --timeout=120s
kubectl -n monitoring wait --for=condition=Ready externalsecret/litellm-prometheus-job-credentials --timeout=120s
kubectl -n monitoring get pvc wal-prometheus-agent-0
kubectl -n monitoring rollout status statefulset/prometheus-agent --timeout=300s
kubectl -n monitoring logs prometheus-agent-0 -c validate-config
kubectl -n monitoring logs prometheus-agent-0 -c prometheus-agent --since=5m
```

Expect the disk to be Bound, config validation to succeed and one Ready Agent pod.
K3s pulls the pinned image if absent. Successful startup is only the first check:
continue with [VERIFY.md](VERIFY.md) before retiring anything.
