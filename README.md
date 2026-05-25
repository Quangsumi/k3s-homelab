# Homelab K3s Platform

This README documents the current homelab Kubernetes setup, the technologies used, why they were chosen, how they connect together, and the main issues encountered during the build.

The cluster is designed around a small Raspberry Pi control-plane node plus worker nodes, with GitOps-style management through Argo CD, persistent storage through Longhorn, LAN LoadBalancer IPs through MetalLB, and remote access through Tailscale Ingress.

---

## 1. High-Level Architecture

```mermaid
flowchart TB
    subgraph Users["Users / Clients"]
        LAN["LAN clients<br/>192.168.63.0/24"]
        Tailnet["Tailscale tailnet devices"]
        Internet["Public Internet users<br/>(only for Funnel-enabled apps)"]
        PiScreen["Raspberry Pi screen / kiosk browser"]
    end

    subgraph Network["Access Layer"]
        MetalLB["MetalLB<br/>LAN LoadBalancer IPs<br/>192.168.63.200-210"]
        TS["Tailscale Operator<br/>Ingress + MagicDNS + HTTPS"]
        Funnel["Tailscale Funnel<br/>optional public HTTPS"]
    end

    subgraph Cluster["K3s Cluster"]
        RPIVN["rpivn<br/>Raspberry Pi<br/>control-plane<br/>192.168.63.102"]
        Winterfall["winterfall<br/>worker<br/>192.168.63.148"]
        SuperWorker["super-worker<br/>experimental worker<br/>VirtualBox VM"]
    end

    subgraph GitOps["GitOps Layer"]
        GitHub["GitHub repo<br/>homelab-k8s"]
        ArgoCD["Argo CD<br/>manual sync first<br/>no auto-sync/prune/self-heal initially"]
    end

    subgraph Apps["Applications"]
        PiDash["pi-dashboard<br/>stateless dashboard"]
        K8sDash["Kubernetes Dashboard<br/>stateless admin UI"]
        Kuma["Uptime Kuma<br/>stateful monitoring UI"]
        LiteLLM["LiteLLM<br/>LLM gateway/API"]
        Postgres["Postgres<br/>LiteLLM database"]
        PgExporter["Postgres Exporter<br/>metrics only"]
        Prom["Prometheus<br/>metrics database"]
        Grafana["Grafana<br/>dashboards/UI"]
    end

    subgraph Storage["Storage Layer"]
        Longhorn["Longhorn<br/>distributed block storage"]
        PVCs["PVCs<br/>Postgres / Uptime Kuma / Prometheus / Grafana"]
        Replicas["Longhorn replicas<br/>2 copies on trusted storage nodes"]
    end

    LAN --> MetalLB
    Tailnet --> TS
    Internet --> Funnel --> TS
    PiScreen --> PiDash

    MetalLB --> Apps
    TS --> Apps

    GitHub --> ArgoCD
    ArgoCD --> Apps

    Apps --> PVCs
    PVCs --> Longhorn
    Longhorn --> Replicas

    RPIVN --- Winterfall
    Winterfall --- SuperWorker

    Apps -.scheduled on.-> RPIVN
    Apps -.scheduled on.-> Winterfall
    Apps -.experimental only.-> SuperWorker
```

---

## 2. Current Node Roles

| Node | Role | Notes |
|---|---|---|
| `rpivn` | K3s control-plane, Raspberry Pi | Main control-plane node. Lightweight workloads can run here. |
| `winterfall` | Worker | Trusted worker and Longhorn storage node. |
| `super-worker` | Experimental worker | VirtualBox test worker. It had Longhorn CSI/mount issues before, so it should not be used for trusted Longhorn-backed workloads unless confirmed stable. |

Recommended labels used in the cluster:

```bash
sudo kubectl label node rpivn storage=longhorn --overwrite
sudo kubectl label node winterfall storage=longhorn --overwrite

sudo kubectl label node rpivn node.longhorn.io/create-default-disk=true --overwrite
sudo kubectl label node winterfall node.longhorn.io/create-default-disk=true --overwrite
```

Do **not** label `super-worker` with `storage=longhorn` unless it is stable enough for persistent workloads.

---

## 3. Main Design Principles

### 3.1 Keep the Pi lightweight

The Raspberry Pi can run the cluster, but the setup avoids unnecessary background work:

- Argo CD runs in Pi-friendly mode.
- Optional Argo CD components such as Dex, notifications, and ApplicationSet can be disabled or scaled down.
- Prometheus and Grafana can be scaled down when not needed.
- Kiosk browser should use Chromium/Openbox instead of a heavy full desktop browser setup.

### 3.2 Use GitOps, but safely

Argo CD is used to manage manifests, but the first phase uses conservative options:

```text
Manual sync only
No auto-sync
No prune
No self-heal
Force off
```

This prevents Argo CD from deleting or overwriting resources accidentally while apps are being migrated gradually.

### 3.3 Treat stateful apps differently

Stateless apps can be replaced easily. Stateful apps need care because they depend on PVCs.

Stateful apps in this cluster:

- Uptime Kuma
- Postgres
- Prometheus
- Grafana
- Longhorn itself

Safe migration rules:

- Do not delete namespaces that contain important PVCs.
- Do not rename PVCs.
- Do not shrink PVC sizes.
- Do not change `storageClassName`.
- Do not scale SQLite-style apps like Uptime Kuma above 1 replica.
- Use `strategy.type: Recreate` for Uptime Kuma.

---

## 4. Networking Overview

```mermaid
flowchart LR
    subgraph LAN["LAN Access"]
        ClientLAN["LAN Browser"]
        LBIP["MetalLB IP<br/>example: 192.168.63.201"]
    end

    subgraph Tailnet["Tailscale Access"]
        Device["Tailnet Device"]
        MagicDNS["MagicDNS hostname<br/>app.tailee75a4.ts.net"]
    end

    subgraph Public["Optional Public Access"]
        PublicUser["Internet User"]
        Funnel["Tailscale Funnel<br/>public HTTPS"]
    end

    subgraph K8s["Kubernetes"]
        Ingress["Tailscale Ingress"]
        SVC["Kubernetes Service<br/>ClusterIP or LoadBalancer"]
        Pod["Application Pod"]
    end

    ClientLAN --> LBIP --> SVC --> Pod
    Device --> MagicDNS --> Ingress --> SVC --> Pod
    PublicUser --> Funnel --> Ingress
```

### 4.1 MetalLB

MetalLB provides LAN LoadBalancer IPs for services.

Known service examples:

| App | Example LAN IP | Notes |
|---|---:|---|
| Uptime Kuma | `192.168.63.201` | Port 80 to pod port 3001 |
| Kubernetes Dashboard | `192.168.63.203` | Port 443 to pod port 8443 or Kong proxy, depending on version |
| Longhorn UI | `192.168.63.204` | Optional |
| LiteLLM | `192.168.63.205` | API/UI |
| Prometheus | `192.168.63.206` | Metrics UI |

MetalLB is useful for same-LAN access without NodePort.

### 4.2 Tailscale Ingress

Tailscale Ingress provides HTTPS access using Tailscale hostnames.

Examples:

```text
https://pi-dashboard.tailee75a4.ts.net
https://uptime-kuma.tailee75a4.ts.net
https://litellm.tailee75a4.ts.net
https://prometheus.tailee75a4.ts.net
https://grafana.tailee75a4.ts.net
https://longhorn.tailee75a4.ts.net
https://argocd.tailee75a4.ts.net
```

A Tailscale Ingress hostname comes from:

```yaml
tls:
  - hosts:
      - app-name
```

This means Tailscale creates an HTTPS hostname like:

```text
https://app-name.<tailnet>.ts.net
```

### 4.3 Tailnet-only vs Funnel

Tailnet-only Ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-tailnet
  namespace: app-namespace
spec:
  ingressClassName: tailscale
  defaultBackend:
    service:
      name: app-service
      port:
        number: 80
  tls:
    - hosts:
        - app-name
```

Public Funnel Ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-funnel
  namespace: app-namespace
  annotations:
    tailscale.com/funnel: "true"
spec:
  ingressClassName: tailscale
  defaultBackend:
    service:
      name: app-service
      port:
        number: 80
  tls:
    - hosts:
        - app-name
```

Recommended access policy:

| Service | Recommended Access |
|---|---|
| pi-dashboard | Tailnet or Funnel, depending on sensitivity |
| Uptime Kuma | Tailnet-only preferred |
| Kubernetes Dashboard | Tailnet-only |
| Longhorn UI | Tailnet-only |
| Prometheus | Tailnet-only |
| Grafana | Tailnet-only |
| Argo CD | Tailnet-only |
| LiteLLM | Tailnet-only or carefully protected public access |

Public Funnel makes the service reachable from the internet. Tailscale ACLs protect tailnet access, but public Funnel needs app-level authentication because it is no longer limited to tailnet devices.

---

## 5. Storage Overview: Longhorn

Longhorn is used as the default distributed storage layer.

```mermaid
flowchart TB
    App["Stateful Pod<br/>example: Uptime Kuma / Postgres"]
    PVC["PVC<br/>storageClassName: longhorn"]
    Volume["Longhorn Volume"]
    Replica1["Replica 1<br/>rpivn disk"]
    Replica2["Replica 2<br/>winterfall disk"]

    App --> PVC --> Volume
    Volume --> Replica1
    Volume --> Replica2
```

### 5.1 Important Longhorn Settings

Longhorn was installed with settings equivalent to:

```bash
helm install longhorn longhorn/longhorn \
  --namespace longhorn-system \
  --set persistence.defaultClassReplicaCount=2 \
  --set defaultSettings.createDefaultDiskLabeledNodes=true \
  --set defaultSettings.storageOverProvisioningPercentage=100
```

Meaning:

- New Longhorn volumes default to 2 replicas.
- Longhorn only creates default disks on nodes labeled with `node.longhorn.io/create-default-disk=true`.
- Storage over-provisioning is limited to 100%.

### 5.2 Replica Mental Model

A stateful app like Uptime Kuma should usually have:

```text
1 app pod
1 Kubernetes PVC
1 Longhorn volume
2 Longhorn storage replicas
```

Longhorn replicas are block-level storage copies. They are not the same as application replicas.

### 5.3 PVC Size Mental Model

A PVC request like:

```yaml
resources:
  requests:
    storage: 5Gi
```

means the volume’s logical requested capacity is 5Gi. Longhorn is thin-provisioned, so actual disk usage grows as data is written, but scheduling and safety calculations still use the requested size and replica count.

With 2 Longhorn replicas, a 5Gi volume needs enough capacity on two storage nodes.

### 5.4 Snapshots

Longhorn snapshots are point-in-time snapshots of a volume. They are not full copies at the beginning; they grow as blocks change.

Snapshots are not the same as external backups. For real disaster recovery, use Longhorn backup targets later.

---

## 6. GitOps with Argo CD

Argo CD watches Git and compares desired state with live Kubernetes state.

```mermaid
sequenceDiagram
    participant Dev as User edits Git repo
    participant Git as GitHub
    participant Argo as Argo CD
    participant K8s as Kubernetes API
    participant Pods as Workloads

    Dev->>Git: Commit and push manifest changes
    Argo->>Git: Poll repo / detect change
    Argo->>Argo: Render Kustomize or Helm
    Argo->>K8s: Compare desired vs live state
    Argo-->>Dev: Shows OutOfSync
    Dev->>Argo: Manual Sync
    Argo->>K8s: Apply desired manifests
    K8s->>Pods: Create/update pods/services/ingress/PVCs
```

### 6.1 Sync Policy Used During Migration

For safety, applications are created without:

```yaml
syncPolicy:
  automated:
```

So Argo CD does not automatically sync.

Safe sync options:

```text
Prune: OFF
Force: OFF
Auto-create namespace: ON
Apply Only: optional
```

### 6.2 How Kustomize Works with Argo CD

If a folder has:

```text
apps/litellm-stack/
  01-secrets.yaml
  02-postgres.yaml
  03-postgres-exporter.yaml
  04-litellm-config.yaml
  05-litellm.yaml
  06-prometheus.yaml
  07-grafana.yaml
  kustomization.yaml
```

and `kustomization.yaml` contains:

```yaml
resources:
  - 01-secrets.yaml
  - 02-postgres.yaml
  - 03-postgres-exporter.yaml
```

then Argo CD only renders and applies those three files.

Later, adding more files to `kustomization.yaml` makes the app OutOfSync. Manual sync applies the new desired resources.

If a resource is removed from `kustomization.yaml`:

- With prune off, Argo CD does not delete it.
- With prune on, Argo CD may delete it.

During migration, keep prune off.

---

## 7. Applications

## 7.1 pi-dashboard

### Purpose

`pi-dashboard` is a lightweight dashboard app intended to be displayed on the Raspberry Pi screen, usually through a kiosk browser.

### Type

Stateless.

### Access

- Tailscale Ingress
- Optional LAN access through MetalLB
- Local Pi kiosk browser

### Notes

The Pi browser setup should avoid heavy desktop overhead. Chromium kiosk mode with a minimal X/Openbox setup is preferred over a full browser session.

Example kiosk launch pattern:

```bash
DISPLAY=:0 chromium --kiosk --app=http://<dashboard-url>
```

### Argo CD Migration

`pi-dashboard` was moved first because it is stateless and low-risk.

The app folder uses Kustomize:

```text
apps/pi-dashboard/
  namespace.yaml
  deployment.yaml
  service.yaml
  tailscale-ingress.yaml
  kustomization.yaml
```

The old Traefik ingress was intentionally excluded from `kustomization.yaml` if no longer needed.

---

## 7.2 Kubernetes Dashboard

### Purpose

Kubernetes Dashboard provides a web UI for Kubernetes cluster management.

### Type

Stateless.

### Access

Recommended:

```text
Tailnet-only Tailscale Ingress
```

Do not expose Kubernetes Dashboard through public Funnel.

### Migration Notes

The old install used:

```text
https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.0-rc5/aio/deploy/recommended.yaml
```

That old manifest layout is very different from the newer Helm-based Dashboard.

The safer migration approach was:

```text
Delete the old kubernetes-dashboard namespace
Install the newer Helm-based Dashboard through Argo CD
Expose the new service through Tailscale Ingress
```

This avoids version mismatch and ownership conflicts.

### Argo CD Notes

The Dashboard Helm app can be managed by Argo CD, and a separate Argo CD app can manage custom extras like Tailscale Ingress.

Recommended split:

```text
Application 1: kubernetes-dashboard
  source: Helm chart

Application 2: kubernetes-dashboard-extras
  source: Git repo
  contains: Tailscale Ingress
```

### Login

For homelab use, an admin service account token can be generated:

```bash
sudo kubectl -n kubernetes-dashboard create token dashboard-admin
```

Be careful with cluster-admin tokens.

---

## 7.3 Uptime Kuma

### Purpose

Uptime Kuma monitors services and provides a status/alerting UI.

### Type

Stateful.

Uptime Kuma stores data under:

```text
/app/data
```

Usually this includes SQLite database files.

### Storage

Use Longhorn PVC.

Important rules:

```text
replicas: 1
strategy.type: Recreate
mountPath: /app/data
same PVC name
same PVC size or larger
storageClassName: longhorn
```

Example Deployment pattern:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: uptime-kuma
  namespace: uptime-kuma
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: uptime-kuma
  template:
    metadata:
      labels:
        app: uptime-kuma
    spec:
      nodeSelector:
        storage: longhorn
      containers:
        - name: uptime-kuma
          image: louislam/uptime-kuma:1
          ports:
            - name: http
              containerPort: 3001
          volumeMounts:
            - name: data
              mountPath: /app/data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: uptime-kuma-data
```

### Access

- Tailscale tailnet-only recommended
- Optional MetalLB LAN IP, example `192.168.63.201`

### Argo CD Migration

Use adoption, not reinstall.

Safe steps:

1. Snapshot the Longhorn volume.
2. Put the same PVC name and deployment/service names in Git.
3. Create Argo CD Application.
4. Manual sync with prune off and force off.
5. Verify PVC remains Bound.

Do **not** delete the namespace or PVC during migration.

---

## 7.4 LiteLLM Stack

The `litellm-stack` namespace contains several components:

```text
LiteLLM
Postgres
Postgres Exporter
Prometheus
Grafana
```

Because this stack is heavier, it is moved to Argo CD gradually.

Recommended migration batches:

```text
Batch 1:
  secrets
  postgres
  postgres-exporter

Batch 2:
  prometheus
  grafana

Batch 3:
  litellm config
  litellm deployment/service/ingress
```

---

## 7.5 Secrets

### Purpose

Secrets store:

- Postgres username/password
- LiteLLM master key
- LiteLLM salt key
- Optional OpenRouter/API keys
- Grafana admin credentials

### Warning

Do not commit real secrets to a public GitHub repo.

Acceptable for homelab:

```text
Private repo
```

Better long-term options:

```text
SealedSecrets
SOPS
External Secrets Operator
1Password/Vault integration
```

Important Postgres warning:

Changing the Kubernetes Secret later does not automatically change the password inside an already-initialized Postgres database.

---

## 7.6 Postgres

### Purpose

Postgres is the database backend for LiteLLM.

### Type

Stateful.

### Storage

Longhorn PVC.

Important rules:

```text
StatefulSet preferred
replicas: 1
PVC name stable
storageClassName: longhorn
do not shrink PVC
nodeSelector: storage=longhorn
```

### Argo CD Migration

Postgres should be moved carefully:

- Keep the existing PVC.
- Do not delete the namespace.
- Do not change password secrets unless intentionally migrating DB credentials.
- Manual sync only.
- Prune off.

---

## 7.7 Postgres Exporter

### Purpose

Postgres Exporter exposes Postgres metrics for Prometheus.

### Type

Stateless.

### Access

Internal only.

It does not need a public UI.

Prometheus scrapes it on port `9187`.

### Pros

- Lightweight.
- Gives useful DB metrics.
- Helps Grafana dashboards show Postgres health.

### Cons

- Slight extra CPU/RAM usage.
- Adds another deployment to maintain.

---

## 7.8 Prometheus

### Purpose

Prometheus scrapes and stores metrics.

### Type

Stateful.

### Storage

Longhorn PVC.

### Notes

Prometheus can become heavy on the Pi if retention, scrape frequency, or target count is too high.

Recommended Pi-friendly settings:

```yaml
resources:
  requests:
    cpu: 50m
    memory: 256Mi
  limits:
    memory: 768Mi
```

If Prometheus is OOMKilled, increase memory or reduce scrape/retention.

### LiteLLM Metrics

LiteLLM `/metrics` may require the LiteLLM master key as a Bearer token.

Prometheus can mount the LiteLLM secret and use:

```yaml
authorization:
  credentials_file: /etc/prometheus/secrets/litellm/LITELLM_MASTER_KEY
```

### Scaling Down

Prometheus can be scaled down to save resources:

```bash
sudo kubectl -n litellm-stack scale statefulset prometheus --replicas=0
```

When Argo CD manages it, manual scale-down may show drift unless self-heal is disabled.

---

## 7.9 Grafana

### Purpose

Grafana provides dashboards and visualization on top of Prometheus.

### Type

Stateful if dashboards/users/plugins are stored locally.

### Storage

Longhorn PVC mounted at:

```text
/var/lib/grafana
```

### Permission Requirements

Grafana commonly needs:

```yaml
securityContext:
  runAsUser: 472
  runAsGroup: 472
  fsGroup: 472
```

If Grafana cannot write to `/var/lib/grafana`, check PVC permissions and the security context.

### Prometheus Data Source

Grafana can provision Prometheus automatically:

```yaml
url: http://prometheus:9090
```

### Access

Recommended:

```text
Tailnet-only Tailscale Ingress
```

Avoid public Funnel unless authentication is strong and intentional.

---

## 8. Platform Components

## 8.1 MetalLB

### Purpose

MetalLB gives Kubernetes `LoadBalancer` services real LAN IP addresses.

Without MetalLB, a bare-metal K3s cluster does not automatically get cloud LoadBalancer IPs.

### Pros

- Simple LAN access.
- Works well for homelab.
- Avoids NodePort URLs.

### Cons

- LAN-only unless combined with routing/VPN.
- IP pool must not conflict with DHCP.
- L2 mode depends on local network behavior.

### Recommended Argo CD Management

Separate installation from configuration:

```text
Application: metallb
  manages MetalLB Helm chart

Application: metallb-config
  manages IPAddressPool and L2Advertisement
```

This allows changing IP pools without touching the MetalLB controller install.

Example config:

```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: homelab-pool
  namespace: metallb-system
spec:
  addresses:
    - 192.168.63.200-192.168.63.210
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: homelab-l2
  namespace: metallb-system
spec:
  ipAddressPools:
    - homelab-pool
```

---

## 8.2 Longhorn

### Purpose

Longhorn provides persistent distributed block storage for Kubernetes PVCs.

### Pros

- Works well on bare-metal.
- Gives UI for volumes, replicas, snapshots, and recovery.
- Replicates storage across nodes.
- Easy to use through Kubernetes PVCs.

### Cons

- Resource-heavy for small devices.
- Requires stable disks and stable networking.
- CSI/engine issues can block pod mounts.
- Time sync problems can break webhook certificates.
- Needs careful upgrades and uninstall procedures.

### Important Operational Notes

Longhorn should be healthy before deploying stateful apps.

Check:

```bash
sudo kubectl -n longhorn-system get pods -o wide
sudo kubectl get sc
sudo kubectl -n longhorn-system get volumes.longhorn.io
```

### Recommended Argo CD Management

Move Longhorn to Argo CD late, not early.

Rules:

```text
Use the same Helm chart version as the current install
Use the same values
Manual sync only
Prune off
Force off
Do not delete the Longhorn Argo CD app casually
```

Values to preserve:

```yaml
persistence:
  defaultClassReplicaCount: 2

defaultSettings:
  createDefaultDiskLabeledNodes: true
  storageOverProvisioningPercentage: 100

preUpgradeChecker:
  jobEnabled: false
```

---

## 8.3 Tailscale Operator

### Purpose

The Tailscale Operator creates Tailscale proxy devices for Kubernetes Services/Ingresses and provides HTTPS hostnames through MagicDNS.

### Pros

- Very convenient remote access.
- No router port-forwarding needed.
- Tailnet-only access is safer for admin tools.
- Funnel can expose selected services publicly.

### Cons

- Requires correct OAuth/tag setup.
- Hostname conflicts can create `-1` suffixes.
- Public Funnel needs app-level auth.
- Ingress service port must match the Kubernetes Service port, not always the container port.

### Tag Model Used

Important tag separation:

```text
tag:k8s-operator
  for the operator itself

tag:k8s
  for proxy devices/services created by the operator
```

Normal machines like `rpivn` or `winterfall` should not be tagged as `tag:k8s-operator`.

---

## 8.4 Argo CD

### Purpose

Argo CD is the GitOps controller. It watches Git and applies Kubernetes desired state.

### Pros

- Git becomes the source of truth.
- Easy to see drift.
- Easy rollback by reverting Git commits.
- Works with Kustomize, raw YAML, and Helm.
- Manual sync mode is safe for learning.

### Cons

- Can delete resources if prune is enabled incorrectly.
- Can undo manual scale-down if self-heal is enabled.
- Adds its own resource usage.
- Managing Argo CD with Argo CD is possible but more complex.

### Pi-Friendly Argo CD

Recommended reduced mode:

```yaml
dex:
  enabled: false

notifications:
  enabled: false

applicationSet:
  replicas: 0

configs:
  cm:
    timeout.reconciliation: 15m
    timeout.reconciliation.jitter: 5m
  params:
    server.insecure: "true"

global:
  nodeSelector:
    kubernetes.io/hostname: rpivn
```

### Why `server.insecure: "true"`?

Tailscale Ingress terminates HTTPS externally. Argo CD can serve HTTP internally behind that HTTPS proxy.

### Managing Argo CD with Argo CD

Possible, but should be done last.

Bootstrap pattern:

```text
1. Install Argo CD manually
2. Create an Argo CD Application for Argo CD itself
3. Use manual sync
4. Avoid auto-prune/self-heal until stable
```

---

## 9. Major Obstacles and Fixes

## 9.1 Helm/Argo CD Install Timeout

### Symptom

During Argo CD Helm install:

```text
http2: client connection lost
TLS handshake timeout
context deadline exceeded
failed to create resource ... Kind=Role
```

### Root Cause

The Kubernetes API server on the Pi was overloaded or slow. The `Kind=Role` message referred to a Kubernetes RBAC Role, not a node role label.

### Fix

- Clean up failed Helm release.
- Use Pi-friendly Helm values.
- Pin Argo CD pods to `rpivn`.
- Disable optional components.
- Increase timeout.
- Scale down heavy workloads temporarily.

Example:

```bash
helm upgrade --install argocd argo/argo-cd \
  -n argocd \
  -f argocd-pi-values.yaml \
  --timeout 60m \
  --wait
```

---

## 9.2 Longhorn Disks Not Available

### Symptom

Longhorn volumes could not schedule because disks were unavailable or nodes were not configured for default disks.

### Root Cause

Longhorn was installed with:

```yaml
createDefaultDiskLabeledNodes: true
```

so Longhorn only auto-created disks on labeled nodes.

### Fix

Label trusted storage nodes:

```bash
sudo kubectl label node rpivn node.longhorn.io/create-default-disk=true --overwrite
sudo kubectl label node winterfall node.longhorn.io/create-default-disk=true --overwrite
```

Create disk path if needed:

```bash
sudo mkdir -p /var/lib/longhorn
```

---

## 9.3 Longhorn Webhook TLS / Time Sync Problem

### Symptom

Errors like:

```text
x509: certificate has expired or is not yet valid
current time is before certificate validity
```

### Root Cause

Node clocks were not in sync. Certificate validation failed because the node time was wrong.

### Fix

- Fix time sync on nodes.
- Restart Longhorn components.
- Recreate Longhorn webhook secrets if necessary.

Relevant cleanup used before:

```bash
sudo kubectl -n longhorn-system delete secret longhorn-webhook-ca longhorn-webhook-tls
sudo kubectl -n longhorn-system rollout restart deploy/longhorn-manager
```

---

## 9.4 Longhorn CSI/Mount Issues on `super-worker`

### Symptoms

```text
driver name driver.longhorn.io not found in registered CSI drivers
mkfs.ext4: Input/output error while writing out and closing file system
```

### Root Cause

The new worker did not have Longhorn CSI fully ready, or the VM/storage stack was not stable.

### Fixes Checked

Install required packages:

```bash
sudo apt install -y open-iscsi nfs-common
sudo systemctl enable --now iscsid
sudo systemctl restart k3s-agent
```

Check CSI node registration:

```bash
sudo kubectl get csinode super-worker -o yaml | grep -A20 driver.longhorn.io
sudo kubectl -n longhorn-system get pods -o wide | grep super-worker
```

### Policy

Keep stateful Longhorn-backed workloads on trusted nodes only:

```yaml
nodeSelector:
  storage: longhorn
```

---

## 9.5 Tailscale Operator OAuth/Tag Problem

### Symptom

Tailscale operator log showed:

```text
creating operator authkey: calling actor does not have enough permissions (403)
```

### Root Cause

The operator needs OAuth client credentials and proper tag ownership. A normal auth key or wrong tag configuration is not enough.

### Fix

Use proper OAuth credentials and tag ownership.

Conceptual tag model:

```json
{
  "tagOwners": {
    "tag:k8s-operator": [],
    "tag:k8s": ["tag:k8s-operator"]
  }
}
```

Only the Tailscale operator device should have `tag:k8s-operator`. Proxy devices should get `tag:k8s`.

---

## 9.6 Tailscale Ingress 502

### Symptom

Uptime Kuma through Tailscale Ingress returned 502.

### Root Cause

Ingress pointed to the wrong service port. It used the container port `3001` instead of the Kubernetes Service port `80`.

### Fix

Point Ingress to the Service port:

```yaml
defaultBackend:
  service:
    name: uptime-kuma
    port:
      number: 80
```

Important rule:

```text
Ingress backend port = Kubernetes Service port
not necessarily the container port
```

---

## 9.7 Tailscale Hostname Suffix `-1`

### Symptom

Dashboard hostname became:

```text
k8s-dashboard-1.tailee75a4.ts.net
```

### Root Cause

A stale or existing Tailscale machine already used the hostname.

### Fix

Remove the old Tailscale device from the admin console or use the new hostname.

---

## 9.8 LiteLLM OOM / Slow Startup

### Symptoms

- LiteLLM crashed or restarted during startup.
- Liveness probe killed it too early.
- Prisma migrations took time.

### Root Cause

LiteLLM was heavier than expected on the Pi, and startup probes were not forgiving enough.

### Fix

Increase memory and add a startup probe.

Recommended pattern:

```yaml
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    memory: 1500Mi

startupProbe:
  tcpSocket:
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 120

readinessProbe:
  httpGet:
    path: /health/readiness
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 10
  failureThreshold: 12

livenessProbe:
  tcpSocket:
    port: http
  initialDelaySeconds: 30
  periodSeconds: 20
  timeoutSeconds: 5
  failureThreshold: 6
```

Keep:

```text
USE_PRISMA_MIGRATE=True
```

This lets LiteLLM manage DB schema migrations.

---

## 9.9 Prometheus Could Not Scrape LiteLLM Metrics

### Symptom

Prometheus got unauthorized responses from LiteLLM `/metrics`.

### Root Cause

LiteLLM metrics endpoint required the master key.

### Fix

Mount the LiteLLM Secret into Prometheus and use bearer authorization:

```yaml
authorization:
  credentials_file: /etc/prometheus/secrets/litellm/LITELLM_MASTER_KEY
```

---

## 9.10 PVC Shrinking

### Problem

PVCs can be expanded but usually cannot be shrunk directly.

### Fix

For disposable data like fresh Prometheus data, it is acceptable to delete and recreate the PVC.

For important data like Postgres or Uptime Kuma, do not shrink in place. Instead:

```text
backup/export
create new smaller PVC
restore/migrate data
```

---

## 10. Pros and Cons of This Setup

## Pros

- Full homelab Kubernetes platform.
- GitOps through Argo CD.
- Remote HTTPS access without router port forwarding through Tailscale.
- LAN LoadBalancer services through MetalLB.
- Persistent replicated storage through Longhorn.
- Good observability path with Prometheus + Grafana.
- LiteLLM gets a real Postgres backend.
- Apps can be migrated gradually.
- Manual sync makes Argo CD safer while learning.

## Cons

- Heavy stack for a Raspberry Pi.
- Longhorn consumes noticeable CPU/RAM and requires stable nodes.
- Prometheus/Grafana can become resource-heavy.
- Argo CD adds another controller to maintain.
- Public Funnel can expose apps if used carelessly.
- Secrets in Git need a better long-term solution.
- SQLite apps like Uptime Kuma should not be scaled horizontally.
- Managing platform apps through Argo CD requires caution.

---

## 11. Recommended Argo CD Migration Order

Already done or recommended:

```text
1. pi-dashboard
2. Kubernetes Dashboard
3. Uptime Kuma
4. litellm-stack batch 1:
   - secrets
   - postgres
   - postgres-exporter
5. litellm-stack batch 2:
   - prometheus
   - grafana
6. litellm-stack batch 3:
   - litellm config
   - litellm deployment/service/ingress
7. MetalLB config
8. Tailscale Ingress extras
9. MetalLB Helm install
10. Longhorn Helm install
11. Argo CD manages Argo CD itself
```

Platform components should be moved later because other apps depend on them.

---

## 12. Recommended Repository Structure

```text
homelab-k8s/
  apps/
    pi-dashboard/
      namespace.yaml
      deployment.yaml
      service.yaml
      tailscale-ingress.yaml
      kustomization.yaml

    kubernetes-dashboard-extras/
      tailscale-ingress.yaml
      kustomization.yaml

    uptime-kuma/
      namespace.yaml
      pvc.yaml
      deployment.yaml
      service.yaml
      service-lb.yaml
      tailscale-ingress.yaml
      kustomization.yaml

    litellm-stack/
      00-namespace.yaml
      01-secrets.yaml
      02-postgres.yaml
      03-postgres-exporter.yaml
      04-litellm-config.yaml
      05-litellm.yaml
      06-prometheus.yaml
      07-grafana.yaml
      kustomization.yaml

  platform/
    metallb-config/
      ipaddresspool.yaml
      l2advertisement.yaml
      kustomization.yaml

    longhorn/
      app.yaml

    argocd/
      app.yaml

  argocd-apps/
    pi-dashboard.yaml
    kubernetes-dashboard.yaml
    kubernetes-dashboard-extras.yaml
    uptime-kuma.yaml
    litellm-stack.yaml
    metallb-config.yaml
```

Later, `argocd-apps/` can be managed by a root Argo CD app, often called an app-of-apps pattern.

---

## 13. Useful Commands

### Cluster

```bash
sudo kubectl get nodes -o wide
sudo kubectl get pods -A -o wide
sudo kubectl get sc
```

### Argo CD

```bash
sudo kubectl -n argocd get pods -o wide
sudo kubectl -n argocd get applications
```

### Longhorn

```bash
sudo kubectl -n longhorn-system get pods -o wide
sudo kubectl -n longhorn-system get svc
```

### PVCs

```bash
sudo kubectl get pvc -A
```

### MetalLB

```bash
sudo kubectl -n metallb-system get pods -o wide
sudo kubectl -n metallb-system get ipaddresspool,l2advertisement
```

### Tailscale Ingresses

```bash
sudo kubectl get ingress -A -o wide
```

### LiteLLM Stack

```bash
sudo kubectl -n litellm-stack get pod,pvc,svc,ingress -o wide
sudo kubectl -n litellm-stack logs deploy/postgres-exporter --tail=100
sudo kubectl -n litellm-stack logs statefulset/postgres --tail=100
sudo kubectl -n litellm-stack logs statefulset/prometheus --tail=100
sudo kubectl -n litellm-stack logs deploy/grafana --tail=100
sudo kubectl -n litellm-stack logs deploy/litellm --tail=100
```

---

## 14. Safety Checklist Before Syncing Stateful Apps

Before syncing Uptime Kuma, Postgres, Prometheus, or Grafana:

```text
[ ] Longhorn UI is healthy
[ ] PVC name matches existing PVC
[ ] PVC size is same or larger
[ ] storageClassName is longhorn
[ ] app replicas are correct
[ ] no accidental namespace delete
[ ] prune is off
[ ] force is off
[ ] self-heal is off
[ ] snapshot exists if data matters
```

---

## 15. Future Improvements

Good next steps:

- Move secrets to SOPS or SealedSecrets.
- Add Longhorn backup target.
- Add resource limits to every workload.
- Add Prometheus retention limits.
- Add Grafana dashboards as code.
- Add alerting later.
- Use Argo CD app-of-apps after all apps are stable.
- Add HA control-plane only if more reliable hardware is available.
- Restrict admin UIs to tailnet-only access.
- Keep public Funnel only for intentionally public services.
