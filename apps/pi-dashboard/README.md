### Pod Security Admission (PSA) - Pod YAML validator at creation time.

#### Biteforce maintenance in three steps

| Where | What happened |
|---|---|
| Tombstone | `k3s kubectl -n kube-system create -f -` read the temporary Pod’s JSON from stdin. |
| Pod on Biteforce | A writable `hostPath` mount exposed Biteforce’s `/` at `/host`. `privileged: true` let the script run `chroot /host`. |
| Biteforce host | After `chroot`, `/etc/rancher/k3s` pointed to Biteforce’s config. The script edited it and restarted K3s through systemd. |

**In `pi-dashboard`**, `enforce: restricted` blocks privileged mode and host mounts even when RBAC allows Pod creation. `warn` shows a warning. `audit` adds an audit annotation.

```bash
# See the namespace policy
kubectl get namespace pi-dashboard --show-labels

# Test the privileged request without starting a Pod
kubectl -n pi-dashboard run psa-privileged-check --image=busybox:1.36.1 \
  --privileged --restart=Never --dry-run=server
```

**Expected with Pod-create permission** · `Forbidden` with `violates PodSecurity "restricted:latest"`.

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
