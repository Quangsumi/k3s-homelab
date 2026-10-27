# Homelab GitOps bootstrap

This directory defines the Argo CD application inventory. Workload manifests
stay under `apps/`, `infrastructure/`, `external-services/`, and `rbac/`.
All Git sources deliberately track `main`. Reviewing or pushing this branch
alone does not deploy its contents; do not sync a branch preview into the live
cluster as part of code review.

## Ownership and permissions

Two seed objects are applied manually after Argo CD exists:

- `bootstrap-project.yaml`: restricts the root to this repository, the local
  `argocd` namespace, and `Application`/`AppProject` resources.
- `root-application.yaml`: points to `bootstrap/homelab` and creates the projects
  and 20 child Applications.

Neither seed is included in the root Kustomization. The root cannot manage
itself. Changes to seeds and platform Applications require administrator review;
permissions to create Applications or write in `argocd` are administrative
capabilities, even with a restricted resource list.

| Project | Scope |
| --- | --- |
| `homelab-bootstrap` | Application and AppProject definitions in `argocd` |
| `homelab-platform` | Platform controllers, cluster resources and cross-namespace RBAC |
| `homelab-observability` | Monitoring namespace, Namespace, ClusterRole, ClusterRoleBinding and StorageClass |
| `homelab-workloads` | Explicit application namespaces; Namespace is the only permitted cluster kind |

The root and all children use manual sync except **pi-dashboard**, which keeps
main's existing automatic sync and self-healing, with `prune: false`. There are
no cascading resource finalizers in these definitions. Syncing the root creates
or updates child definitions; it does not initiate manual child syncs. The
existing automated pi-dashboard child can reconcile when its definition changes.

Previously, `apps/pi-dashboard/kustomization.yaml` included its own Application.
Argo CD rendered that Application along with the Deployment and Services, so the
application managed its own control settings. Now the root owns that definition,
and the pi-dashboard child renders only its workload resources. Automatic
workload updates still work.

## Managed inventory

| Child Application | Repository package / purpose |
| --- | --- |
| `priority-classes` | `infrastructure/priority-classes`; sync before any consuming Pods |
| `kube-vip` | `infrastructure/kube-vip`; existing API access must already work |
| `traefik` | `infrastructure/traefik`; K3s HelmChartConfig and dashboard |
| `external-secrets` | ESO chart and `infrastructure/eso` |
| `cert-manager` | cert-manager/trust-manager charts and `infrastructure/cert-manager`, including `pki` |
| `infisical-acme` | Separate enrollment Secret and issuer; manually activate after prerequisites |
| `tailscale-credentials` | `infrastructure/tailscale/credentials`; ESO-owned OAuth Secret |
| `tailscale` | Operator chart, ProxyClass, ProxyGroup and Traefik-facing Service |
| `longhorn` | Chart and `infrastructure/longhorn`; preserve main's worker-only placement |
| `metallb` | Chart and `infrastructure/metallb` |
| `rbac` | Cluster and namespace bindings; PriorityClasses have a separate owner |
| `monitoring` | `apps/monitoring`, including observability storage and cluster RBAC |
| `external-services` | External endpoint Services and routes |
| `kanboard`, `litellm`, `normal-ass-note`, `pi-dashboard`, `postgres`, `stremio` | Corresponding `apps/` packages |
| `argocd` | Chart and `infrastructure/argocd`; adopt last |

Intentional manual boundaries:

- K3s installation, the first working API endpoint and initial Argo CD install.
- Host OIDC/TLS configuration and public CA distribution: see `ansible/` and `pki/`.
- `infrastructure/dns/05-coredns-custom.yaml`: bootstrap DNS, restored before
  controllers need `*.lab` names. It is not a Kustomize package.
- `apps/homelab-dashboard`: external dashboard access helpers with no deployable
  Kustomize package; the optional persistent token is not enabled by this root.
- The ACME canary remains separate and explicitly applied during issuer verification.

## Secret-zero and recovery prerequisites

Never commit kubeconfigs, administrator passwords, repository private keys,
Infisical Universal Auth values, Tailscale OAuth values/auth keys, or private
certificate keys. Public certificates under `pki/` are intentional.

Before seeding, restore:

1. A functioning K3s API, bootstrap DNS, network access to Git/chart repositories
   and `infisical.lab`, and enough Argo CD to run its controller and repo server.
   Initial Argo CD installation must work without the application trust bundle;
   adopt the configured self-management Application only after trust is ready.
2. The `external-secrets` namespace and `Secret/infisical-universal-auth`, with
   `clientId` and `clientSecret`, from secure backup. ESO needs this credential
   before it can fetch anything from Infisical. For example, from protected files
   outside the repository (avoid trailing newlines in credential files):

   ```powershell
   kubectl create namespace external-secrets --dry-run=client -o yaml |
     kubectl apply -f -
   kubectl -n external-secrets create secret generic infisical-universal-auth `
     --from-file=clientId=C:\secure\infisical-client-id.txt `
     --from-file=clientSecret=C:\secure\infisical-client-secret.txt `
     --dry-run=client -o yaml | kubectl apply -f -
   ```

3. Infisical's required secrets, including the Tailscale client ID/secret at
   `/tailscale/OAUTH_CLIENT_ID` and `/tailscale/OAUTH_CLIENT_SECRET` in the `dev`
   environment used by `ClusterSecretStore/infisical`. ESO creates
   `tailscale/Secret/operator-oauth` with keys `client_id` and `client_secret`.
   Tailnet OAuth scopes and tags are described in
   [the Tailscale guide](../infrastructure/tailscale/README.md).

## First bootstrap and dependency gates

After the reviewed changes are merged into main, seed using repository-root paths:

```powershell
kubectl apply -f bootstrap/bootstrap-project.yaml
kubectl apply -f bootstrap/root-application.yaml
```

Inspect the `homelab-bootstrap` diff, then sync it. Application creation order
is not workload readiness order; all manual children still need deliberate syncs.
Project sync wave `-1` only ensures projects exist before their child definitions.

Use this order for a fresh recovery:

1. Sync `priority-classes`. Verify the four `homelab-*` classes exist before
   syncing any chart or workload that references them.
2. Restore/adopt `kube-vip` when appropriate. The root cannot repair an API
   endpoint that is already unreachable; keep direct server access available.
3. Sync `external-secrets` to install the operator and its CRDs. Its Infisical
   store can be NotReady at this stage because the trust bundle is not ready yet.
4. Sync `cert-manager`. This installs cert-manager and trust-manager and renders
   the public CA ConfigMap from `pki/`. trust-manager distributes
   `caddy-trust-bundle` independently of ESO fetching the legacy CA private key.
   Wait for the Bundle and the `external-secrets` namespace's trust ConfigMap,
   then wait for `ClusterSecretStore/infisical` to become Ready. ESO and
   cert-manager's remaining secret-dependent resources should then reconcile.
5. Sync `tailscale-credentials`; wait for its ExternalSecret to be Ready and
   verify that `tailscale/Secret/operator-oauth` exists without decoding it.
6. Sync `longhorn` after preparing two eligible workers as described in
   [its rollout guide](../infrastructure/longhorn/WORKER-ROLLOUT.md).
   Sync `metallb` if the LAN load-balancer path is part of this installation.
7. Sync `tailscale` after reviewing the operator adoption checks below. Its
   routing resources run after the operator's wave; this does not replace the
   credential readiness gate.
8. Sync `traefik` after resolving any host-file ownership described below.
   Confirm Infisical and cert-manager can resolve website names and reach
   Traefik HTTP port 80 for ACME HTTP-01.
9. Review and sync `infisical-acme`. Wait for its enrollment ExternalSecret and
   ClusterIssuer readiness, then run the separate canary procedure in
   [the ACME guide](../infrastructure/cert-manager/infisical-acme/README.md).
   Creating its Application in the root does not activate the issuer.
10. Sync application packages and monitoring after storage, required secrets,
    trust and certificate issuance are ready. Pi-dashboard may already be
    reconciling automatically; complete its external prerequisites first.
11. Sync `rbac` after all referenced namespaces exist, then adopt `argocd`
    self-management last.

Useful readiness checks:

```powershell
kubectl get priorityclasses
kubectl get bundle caddy-trust-bundle
kubectl -n external-secrets get configmap caddy-trust-bundle
kubectl wait --for=condition=Ready clustersecretstore/infisical --timeout=120s
kubectl -n tailscale get externalsecret tailscale-operator-oauth
kubectl -n tailscale get secret operator-oauth
kubectl get clusterissuer infisical-acme
```

## Adopting an existing cluster

Keep existing Application names and namespaces. Moving their YAML files does
not require deleting and recreating the live Applications.

1. Review a full Argo CD diff before each sync. Preserve the latest deployed
   settings; this change is an ownership migration, not a requested downgrade.
2. Seed the restricted bootstrap project and root as above. Sync the root with
   pruning disabled. It adopts existing child definitions by name. Check any
   existing finalizers and ownership tracking before deletion or pruning.
3. Transfer PriorityClasses from `rbac` by syncing the updated `rbac` child
   **without pruning**, then sync `priority-classes` to adopt the existing
   classes. Do not delete the classes to change their owner. For fresh recovery,
   follow the earlier order instead.
4. Pi-dashboard's Application stops appearing in its own workload source. Keep
   pruning disabled during the transfer to the root; retain automatic workload
   sync/self-healing. Do not delete its Application.
5. For Tailscale, record the installed chart version and release name with
   `helm list -n tailscale` and inspect its non-secret deployment settings.
   Compare them with the pinned Application before syncing. Do not replace
   existing OAuth credentials or change operator identity unintentionally.
   Materialize the matching credentials via ESO first. The Application reuses
   main's resource budgets and control-plane scheduling through
   `infrastructure/tailscale/tailscale-values.yaml`; chart version and hostname
   differences must be reviewed before operator rollout. Argo CD uses Helm to
   render templates; stop using manual Helm upgrades for resources it adopts.
6. For Traefik, check every K3s server for an existing
   `/var/lib/rancher/k3s/server/manifests/traefik-config.yaml` defining the same
   `HelmChartConfig/traefik`. Reconcile its values with the Git version and remove
   the duplicate host-file management through the host recovery workflow before
   syncing the `traefik` child. K3s still owns the packaged Traefik HelmChart;
   Argo CD owns its HelmChartConfig, not a second Traefik installation.
7. The deployer policy retains `default/*` during migration and adds all three
   child projects. After confirming no applications remain in `default`, review
   removal of that transitional grant separately. The root remains admin-only.

## Validation without a cluster

Install Python dependencies and use Kustomize v5.8.1 (or `kubectl kustomize`),
then run from the repository root:

```bash
python3 -m pip install -r scripts/requirements-gitops.txt
python3 scripts/validate-gitops.py
python3 scripts/validate-gitops.py --helm
```

`--helm` downloads all pinned charts and renders them with their configured
values, including Tailscale's external values file. It uses an isolated temporary
Helm configuration/cache. CI runs this full check. The validator also checks:

- All Kustomizations render, including the separate ACME canary.
- Every top-level deployable package has a child Application.
- Repositories, namespaces and resource kinds comply with their AppProjects.
- Children do not render their own Argo CD control objects.
- Rendered resources do not have competing child owners.
- PriorityClass references resolve and Helm does not create the ESO OAuth Secret.

These checks do not prove live readiness, validate all Kubernetes schemas, or
establish the current installed chart versions. Review Argo CD diffs and perform
readiness checks during an authorized deployment.

## Recovery and deletion

Deleting an Application is not the uninstall workflow. Automated pruning and
cascading finalizers are absent from these definitions, but existing live
finalizers must still be inspected. Removing a manifest leaves resources to be
reviewed for explicit retirement. Never use pruning to transfer ownership of
PriorityClasses, storage resources or the pi-dashboard Application.
