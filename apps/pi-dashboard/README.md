### Pod Security Admission (PSA) - Pod YAML validator at creation time.

#### Biteforce maintenance

Tombstone submitted the Pod JSON on stdin with `k3s kubectl -n kube-system create -f -`. The privileged Pod ran on Biteforce and mounted the host’s `/` at `/host`.

```text
Biteforce host     /etc/rancher/k3s
Inside the Pod     /host/etc/rancher/k3s   ← hostPath mount
After chroot       /etc/rancher/k3s        ← chroot /host
```

All three paths point to Biteforce’s K3s config. The script edited it and restarted K3s.

**In `pi-dashboard`, `enforce: restricted` rejects either `privileged: true` or a `hostPath` mount.** `warn` and `audit` only report.

```bash
kubectl get ns pi-dashboard --show-labels
kubectl -n pi-dashboard run psa-check --image=busybox:1.36.1 \
  --privileged --restart=Never --dry-run=server
```

With permission to create Pods, expect `Forbidden` with `violates PodSecurity "restricted:latest"`. The dry run starts no Pod.

```
Argo CD submits Deployment
        ↓
Deployment controller requests a new Pod
        ↓
Kubernetes API server reads labels on namespace "pi-dashboard"
        ↓
Pod Security Admission examines the Pod YAML
        ↓
Compliant Pod → accepted and started
Bad Pod       → rejected; it never starts
```
**3 modes:**
```
enforce, warn, audit
```

**3 levels:**
```
privileged → effectively unrestricted
baseline   → blocks commonly dangerous behavior
restricted → requires strong pod hardening
```
**eg:**
```
pod-security.kubernetes.io/enforce: restricted
- restricted means Reject the pod creation if "restricted" requirements are not met
- search about "restricted/baseline/privileged" requirements
```
| Restricted requirement | Pi Dashboard |
|---|---|
| Must run non-root | `runAsNonRoot: true`, UID `101` |
| Cannot gain more privileges | `allowPrivilegeEscalation: false` |
| Must drop Linux capabilities | `drop: ["ALL"]` |
| Must use seccomp | `RuntimeDefault` |
| Cannot be privileged | No `privileged: true` |
| Cannot use host networking | No `hostNetwork: true` |
| Cannot access host files | No `hostPath` volume |
| Cannot use host PID/IPC | Not configured |
```
If insecure pod was already running before adding labels: PSA does not kill existing pods
But when that pod is deleted/restarted/rescheduled/replaced: PSA checks it and rejects it
```
