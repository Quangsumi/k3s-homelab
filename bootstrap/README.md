# Homelab GitOps bootstrap

This directory contains the Argo CD control plane for the repository. It does
not contain application Deployments, Services, or credentials.

## Ownership

`root-application.yaml` is the one seed object applied manually after Argo CD
already exists. It points to `bootstrap/homelab`, which renders:

- `AppProject/homelab-platform`
- `AppProject/homelab-workloads`
- one child `Application` for each managed platform or workload package

The root Application is intentionally not listed in any Kustomization. Argo CD
therefore does not recursively manage the seed object that grants it ownership.

All root and child Applications use manual sync. There is no automatic pruning
and there are no cascading resource finalizers in this bootstrap.

## Secret-zero boundary

Never commit the following bootstrap inputs:

- kubeconfig files
- Argo CD administrator credentials
- repository credentials or private keys
- Infisical Universal Auth credentials
- Tailscale OAuth credentials or auth keys
- private certificate keys

The Infisical Universal Auth Kubernetes Secret is the ESO "secret zero." ESO
cannot fetch that credential from Infisical because it needs the credential to
authenticate to Infisical in the first place. Restore it out of band. After
that, ESO can materialize downstream credentials, including Tailscale OAuth,
from Infisical.

## Manual bootstrap prerequisites

These are intentional manual recovery inputs. They are not stored in this
repository and are not created by the root Application.

1. **Install enough Argo CD to create the root Application.**
   Install Argo CD through the recovery method for this cluster. At minimum,
   `Application` and `AppProject` CRDs, the application controller, and the repo
   server must be functional. Keep the initial install outside this root
   Application to avoid a bootstrap dependency loop.

   ```powershell
   kubectl get crd applications.argoproj.io appprojects.argoproj.io
   kubectl -n argocd get pods
   ```

2. **Restore the Infisical Universal Auth Kubernetes Secret—the ESO "secret
   zero."** Restore `Secret/infisical-universal-auth` in namespace
   `external-secrets` from a secure backup. It must contain the keys `clientId`
   and `clientSecret`. Never put their values in Git or shell history. One safe
   option is to load each value from a protected local file:

   ```powershell
   kubectl create namespace external-secrets --dry-run=client -o yaml |
     kubectl apply -f -

   kubectl -n external-secrets create secret generic infisical-universal-auth `
     --from-file=clientId=C:\secure\infisical-client-id.txt `
     --from-file=clientSecret=C:\secure\infisical-client-secret.txt `
     --dry-run=client -o yaml |
     kubectl apply -f -
   ```

   The protected files must not live in this repository. Remove them securely
   after restoring the Secret if they are only temporary recovery files.

3. **Ensure `ClusterSecretStore/infisical` is valid.** Sync the
   `external-secrets` child first, then verify the store can authenticate and
   trust the Infisical TLS certificate:

   ```powershell
   kubectl wait --for=condition=Ready clustersecretstore/infisical --timeout=120s
   kubectl describe clustersecretstore infisical
   ```

   Do not sync any credential-consuming child while this resource is not
   `Ready=True`.

4. **Create a Tailscale OAuth client in the Tailscale administration console.**
   In the tailnet policy, define `tag:k8s-operator` and `tag:k8s`, and make
   `tag:k8s-operator` an owner of `tag:k8s`. Create the OAuth client with the
   `tag:k8s-operator` tag and Read/Write access for General > Services,
   Devices > Core, and Keys > Auth Keys.

5. **Store that OAuth client ID and secret in Infisical.** In the `dev`
   environment used by `ClusterSecretStore/infisical`, create:

   - `/tailscale/OAUTH_CLIENT_ID`
   - `/tailscale/OAUTH_CLIENT_SECRET`

   `Application/tailscale-credentials` syncs the corresponding
   `ExternalSecret`. ESO maps those two values into
   `tailscale/Secret/operator-oauth` using the chart-required keys `client_id`
   and `client_secret`. The OAuth values never belong in Kustomize or Helm
   values in Git.

## Tailscale and MetalLB ownership

- `tailscale-credentials` manages only the ExternalSecret that produces the
  operator OAuth Secret.
- `tailscale` installs the pinned official Tailscale operator chart and manages
  the ProxyGroup plus Traefik-facing Tailscale LoadBalancer Service.
- `metallb` installs the pinned official MetalLB chart and manages the local
  address pool and advertisement resources.

These children remain manual-sync Applications. Tailscale is the private
Tailnet entry path; MetalLB is the LAN load-balancer path. They solve different
network entry problems and can coexist.

## Local validation

Render the bootstrap control resources without contacting the cluster:

```powershell
kubectl kustomize bootstrap/homelab
```

The output should contain only `AppProject` and `Application` resources.

Render every child Kustomize source before committing:

```powershell
$paths = @(
  'apps/litellm',
  'apps/monitoring',
  'apps/normal-ass-note',
  'apps/pi-dashboard',
  'apps/postgres',
  'external-services',
  'infrastructure/argocd',
  'infrastructure/cert-manager',
  'infrastructure/eso',
  'infrastructure/longhorn',
  'infrastructure/metallb',
  'infrastructure/tailscale/credentials',
  'infrastructure/tailscale',
  'rbac'
)

foreach ($path in $paths) {
  kubectl kustomize $path | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Kustomize render failed: $path"
  }
}
```

This validates repository sources only. Argo CD renders each Helm source at
sync time; inspect the child Application diff before syncing it.

## First bootstrap

1. Complete the five manual prerequisites above.
2. Ensure Argo CD can read this repository.
3. Commit and push the reviewed manifests.
4. Apply the seed once:

   ```powershell
   kubectl apply -f bootstrap/root-application.yaml
   ```

5. Inspect the `homelab-bootstrap` diff in Argo CD.
6. Sync `homelab-bootstrap`. This creates the projects and child Applications,
   but does not sync the children.
7. Sync children deliberately in dependency order.

Suggested initial order:

1. `external-secrets`
2. verify `ClusterSecretStore/infisical` is `Ready=True`
3. `tailscale-credentials`
4. verify `ExternalSecret/tailscale-operator-oauth` is Ready and
   `Secret/operator-oauth` exists in namespace `tailscale`
5. `cert-manager`
6. `longhorn`
7. `metallb` when LAN load balancing is part of the active design
8. `tailscale`
9. stateless workloads
10. PVC-backed workloads
11. `rbac` after all referenced namespaces exist
12. `argocd` self-management last

Useful Tailscale checks after the two child syncs are:

```powershell
kubectl -n tailscale get externalsecret tailscale-operator-oauth
kubectl -n tailscale get secret operator-oauth
kubectl -n tailscale get pods
kubectl -n tailscale get proxygroup traefik-ingress-proxies
```

Do not print or decode `Secret/operator-oauth` during routine validation.

## Recovery and deletion

Deleting a child Application is not used as an application-uninstall workflow.
Because cascading finalizers and automated pruning are intentionally absent,
removing a control object does not silently authorize deletion of its managed
workloads. Plan and verify destructive removal separately.