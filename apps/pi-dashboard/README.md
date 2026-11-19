### Pod Security Admission (PSA) - Pod YAML validator at creation time.

#### Recollect Biteforce Incident

Tombstone submitted a privileged Pod. The privileged Pod ran on Biteforce and mounted the Biteforce's whole filesystem `/` at `/host` inside the pod.

```bash
kubectl -n pi-dashboard create -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: biteforce-maintenance-check
spec:
  nodeName: biteforce
  hostNetwork: true
  hostPID: true
  automountServiceAccountToken: false
  containers:
    - name: maintenance
      image: busybox:1.36.1
      securityContext: {privileged: true}
      volumeMounts:
        - {name: host-root, mountPath: /host}
  volumes:
    - name: host-root
      hostPath: {path: /, type: Directory}
YAML
```

```text
Biteforce host     /
Inside the Pod     /host                   ← hostPath mount
After chroot       /                       ← chroot /host
```

All three paths point to Biteforce’s `/`. The script from Tombstone then can manipulate Biteforce.

With Pod Security Admission (PSA), it can block the privileged Pod and its host mount.

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
