# Longhorn 1.11.2 worker-only rollout

These changes are local only. Do not sync while the second worker is unavailable.
No node labels are created by these manifests: label existing Kubernetes Nodes manually.

## Intended placement

- Only workers labeled `longhorn-enabled=true` run Longhorn chart components.
- `global.nodeSelector` covers manager, UI, and driver deployer.
- `defaultSettings.systemManagedComponentsNodeSelector` covers system-managed components.
- CSI attacher, provisioner, resizer, and snapshotter each have two replicas with hard node anti-affinity.
- OAuth2 proxy also selects labeled workers; its existing hard anti-affinity is preserved.
- Longhorn UI keeps the chart's default soft anti-affinity and two replicas.
- Volume data replica count remains two. CSI pod count does not control data replication.
- Control-plane replica scheduling must remain disabled in Longhorn; selectors do not evacuate existing data.

## 1. Restore and inspect both workers

Run these yourself against the intended cluster:

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get --raw='/readyz?verbose'
kubectl -n longhorn-system get pods -o wide
kubectl -n longhorn-system get nodes.longhorn.io
kubectl -n longhorn-system get volumes.longhorn.io
kubectl -n longhorn-system get replicas.longhorn.io -o custom-columns='NAME:.metadata.name,VOLUME:.spec.volumeName,NODE:.spec.nodeID,STATE:.status.currentState'
```

Proceed only when two intended workers are Ready, Longhorn recognizes both as ready and schedulable, their disks have sufficient capacity, and important volumes have two healthy replicas on separate workers. Fix existing CSI errors/restarts first. Confirm the workers have Longhorn host prerequisites such as open-iscsi and nfs-common.

## 2. Label the intended workers

Replace the placeholder with the actual second worker name. Do not label control-plane nodes.

```powershell
kubectl label node minotaur longhorn-enabled=true --overwrite
kubectl label node <second-worker-name> longhorn-enabled=true --overwrite
kubectl get nodes -L longhorn-enabled
```

If a control plane already has this label, remove it with `kubectl label node <control-plane-name> longhorn-enabled-`.

## 3. Confirm the control planes are storage-free

In Longhorn UI, keep replica scheduling disabled on every control plane and its disks. Check actual replicas and attached volumes, not just the scheduling switch.

If replicas remain there, request Longhorn replica eviction and wait for healthy replacement copies on the workers. Never delete replica data or instance-manager pods to force migration. Move any application using a Longhorn PVC from the control planes to workers. Confirm no volume remains attached to an excluded node.

## 4. Schedule maintenance and detach volumes

Take a current backup of important data and record existing Longhorn settings and node placement for rollback. Pause application GitOps reconciliation if it would recreate workloads stopped for maintenance. Record replica counts, stop workloads using Longhorn PVCs through their normal maintenance procedure, and wait until all Longhorn volumes show Detached. Include RWX consumers.

Longhorn documents stopping workloads and detaching volumes before changing component node selectors. The change restarts storage components; do not perform storage operations during that transition.

## 5. Publish the reviewed changes and update the Application

When you choose to deploy later, review and commit/push only the intended Longhorn changes to the repository's `main` branch. Do not include unrelated local edits. The Application's second source reads GitHub `main`, so local file edits alone do not update OAuth2 proxy.

Update the existing Application from the local manifest if your parent GitOps application does not manage it:

```powershell
kubectl apply -f infrastructure/longhorn/argocd-app.yaml
```

If a parent application owns this Application, sync that parent instead so it does not overwrite the local update. Then refresh the `longhorn` Application in Argo CD, inspect its diff, and manually Sync. Confirm the diff includes worker selectors, CSI replica counts/anti-affinity, and the OAuth2 proxy placement change. The Application currently has no automated sync configured.

## 6. Verify settings and placement before restarting applications

```powershell
kubectl -n longhorn-system get settings.longhorn.io system-managed-components-node-selector -o yaml
kubectl -n longhorn-system get daemonsets,deployments
kubectl -n longhorn-system get pods -o wide
kubectl -n longhorn-system get deployment csi-attacher -o yaml
kubectl -n longhorn-system get events --sort-by=.metadata.creationTimestamp
```

The effective system-managed selector must be `longhorn-enabled:true`. If the existing setting did not adopt the Helm default, keep volumes detached and set Settings > System Managed Components Node Selector to that exact value in Longhorn UI; then verify again.

Expected results:

- No Longhorn chart pods or OAuth2 proxy pods remain on control planes after reconciliation.
- Each CSI controller Deployment has two ready pods, one per worker.
- OAuth2 proxy has two ready pods, one per worker.
- UI prefers separate workers, but its soft anti-affinity is not a guarantee.
- Existing volumes retain their desired data replica count of two.

If a replica is Pending, inspect `kubectl -n longhorn-system describe pod <pod-name>` for label, taint, capacity, or anti-affinity restrictions. Do not weaken hard anti-affinity merely to conceal a missing worker.

After excluding control planes, Longhorn may show their Longhorn Node records as Down. Verify no replicas or engines remain before removing obsolete Longhorn Node records in the UI; do not delete the Kubernetes Nodes.

## 7. Resume and verify applications

Restore the recorded workload replica counts and resume their GitOps reconciliation. Check volume attachment, mounts, application reads/writes, Longhorn UI login, and two healthy data replicas on separate workers. Kubernetes Ready pods alone do not prove volume I/O or OAuth2 login works.

## Rollback

Keep workloads stopped and volumes detached while reverting selector changes. Restore the previous chart values, OAuth2 placement, and effective system-managed selector, then refresh/sync the previous Git revision. Verify component readiness before resuming workloads. Setting CSI anti-affinity to `soft` temporarily can permit colocation when only one worker is eligible; it does not restore node-failure resilience or a missing data replica.

## References

- [Longhorn 1.11.2 chart values](https://github.com/longhorn/longhorn/blob/v1.11.2/chart/values.yaml)
- [CSI anti-affinity](https://longhorn.io/docs/1.11.2/advanced-resources/deploy/csi-pod-antiaffinity-preset/)
- [Component node-selector maintenance](https://longhorn.io/docs/1.11.2/advanced-resources/deploy/node-selector/)
