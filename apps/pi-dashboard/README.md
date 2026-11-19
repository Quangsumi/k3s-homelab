### Pod Security Admission (PSA) - Pod YAML validator at creation time.

#### Biteforce maintenance example

During K3s maintenance on Biteforce, the script on Tombstone sent a temporary Pod definition to the API using `kubectl create`.

```bash
k3s kubectl -n kube-system create -f -
```

`-f -` read the Pod JSON from standard input. The JSON assigned the Pod to Biteforce, set `privileged: true`, and mounted Biteforce’s `/` at `/host` using a writable `hostPath` volume. Running `chroot /host` inside the Pod made `/etc/rancher/k3s` resolve to Biteforce’s host files. The maintenance script used that access to update the host config and restart K3s.

Check the namespace labels, then test admission with a server-side dry run using an account that can create Pods in `pi-dashboard`.

```bash
kubectl get namespace pi-dashboard --show-labels
kubectl -n pi-dashboard run psa-privileged-check --image=busybox:1.36.1 \
  --privileged --restart=Never --dry-run=server
```

The second command requests privileged mode without mounting host files. Expect `Forbidden` with `violates PodSecurity "restricted:latest"`. The API server evaluates the request without creating a Pod. `enforce: restricted` blocks the request even when RBAC permits Pod creation, while `warn` and `audit` report violations.

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
