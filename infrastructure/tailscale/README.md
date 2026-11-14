# Tailscale Kubernetes operator

Two Argo CD Applications own the Tailscale setup:

- `tailscale-credentials`: an ExternalSecret reads
  `/tailscale/OAUTH_CLIENT_ID` and `/tailscale/OAUTH_CLIENT_SECRET` from Infisical
  and produces `tailscale/Secret/operator-oauth`, with `client_id` and
  `client_secret` keys.
- `tailscale`: renders the pinned official operator chart and this directory's
  routing package, including `ProxyClass/control-plane-proxies`, the three
  ingress proxies, and `kube-system/Service/traefik-tailscale-ha`.

The Helm source loads `tailscale-values.yaml` through Argo CD's `$values`
reference. It preserves main's resource budgets, priority class, control-plane
placement and tolerations. OAuth values are supplied only through the
ESO-managed Secret, not through Helm values or parameters.

## Prerequisites and order

1. Restore Infisical secret-zero, sync the PriorityClasses and ESO/trust
   dependencies, then verify `ClusterSecretStore/infisical` is Ready.
2. Create or recover a dedicated Tailscale OAuth client. Define
   `tag:k8s-operator` and `tag:k8s`; allow the operator tag to own the proxy tag:

   ```json
   {
     "tagOwners": {
       "tag:k8s-operator": [],
       "tag:k8s": ["tag:k8s-operator"]
     }
   }
   ```

   Give the client `tag:k8s-operator` and Read/Write access for General >
   Services, Devices > Core and Keys > Auth Keys. Store its credentials at the
   Infisical paths above, in the store's `dev` environment.
3. Sync `tailscale-credentials` and wait for its ExternalSecret readiness.
4. Inspect the `tailscale` diff and sync only after the OAuth Secret exists.
   Routing custom resources use wave `1`, after the chart's operator/CRDs.

```powershell
kubectl get clustersecretstore infisical
kubectl -n tailscale get externalsecret tailscale-operator-oauth
kubectl -n tailscale get secret operator-oauth
kubectl -n tailscale get pods
kubectl get proxyclass control-plane-proxies
kubectl get proxygroup traefik-ingress-proxies
kubectl -n kube-system get service traefik-tailscale-ha
```

Do not print or decode the OAuth Secret during routine checks. The retained
`01-tailscale-auth.yaml` is main's namespace-only manual recovery helper; it is
not included in the routing Kustomization. Argo CD creates the namespace through
`CreateNamespace=true`.

## Existing installations

Before adoption, compare the installed release name, version, operator identity,
non-secret values and resource ownership with the Application. Preserve existing
credentials and tailnet registrations. Once Argo CD adopts the installation,
stop managing those same resources with manual Helm upgrades. See the complete
[migration procedure](../../bootstrap/README.md#adopting-an-existing-cluster).

## Traffic and Traefik ownership

```text
Tailnet client -> Tailscale Service VIP -> a control-plane proxy replica
  -> traefik-tailscale-ha -> Traefik pods -> workload Service
```

Argo CD's `traefik` Application manages
[`HelmChartConfig/traefik`](../traefik/10-resource-config.yaml), including the
ClusterIP Service, control-plane placement, HTTP/HTTPS/Postgres/SSH entrypoints,
metrics and publishedService override. K3s continues managing the packaged
Traefik chart. Remove duplicate management by a server-side
`manifests/traefik-config.yaml` through the documented host workflow before
adopting this Application; otherwise two reconcilers can overwrite its values.

Tailscale ingress remains private unless a separately reviewed Ingress enables
`tailscale.com/funnel: "true"`. MetalLB is a separate LAN entry path.
