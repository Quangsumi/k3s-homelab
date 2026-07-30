# Tailscale Kubernetes operator

Tailscale is managed by two manual-sync Argo CD child Applications:

- `bootstrap/homelab/applications/tailscale-credentials.yaml` renders this
  directory's `credentials/` package. ESO reads the OAuth client from Infisical
  and owns `tailscale/Secret/operator-oauth`.
- `bootstrap/homelab/applications/tailscale.yaml` installs the pinned official
  `tailscale-operator` Helm chart and renders this directory's routing package.

No OAuth client, auth key, or Kubernetes Secret value is stored in Git.

## Credential flow

```text
Tailscale admin console
  -> OAuth client ID and secret
  -> Infisical dev environment
       /tailscale/OAUTH_CLIENT_ID
       /tailscale/OAUTH_CLIENT_SECRET
  -> ClusterSecretStore/infisical
  -> ExternalSecret/tailscale-operator-oauth
  -> tailscale/Secret/operator-oauth
       client_id
       client_secret
  -> tailscale-operator Helm release
```

The `operator-oauth` Secret must exist before syncing `Application/tailscale`.
The chart mounts it through `oauthSecretVolume`; the secret values are not
passed through Argo CD Helm parameters.

## Tailnet prerequisites

In the Tailscale access policy, create the operator and proxy tags and allow the
operator tag to own the proxy tag:

```json
{
  "tagOwners": {
    "tag:k8s-operator": [],
    "tag:k8s": ["tag:k8s-operator"]
  }
}
```

In the Tailscale administration console, create a dedicated OAuth client with:

- tag: `tag:k8s-operator`
- General > Services: Read and Write
- Devices > Core: Read and Write
- Keys > Auth Keys: Read and Write

Store the generated values in Infisical at the two paths shown above. Do not
commit them to a manifest.

## Sync order

1. Sync `external-secrets` and verify `ClusterSecretStore/infisical` is Ready.
2. Sync `tailscale-credentials`.
3. Verify the ExternalSecret is Ready and the generated Secret exists without
   printing its data.
4. Inspect and sync `tailscale`.

```powershell
kubectl get clustersecretstore infisical
kubectl -n tailscale get externalsecret tailscale-operator-oauth
kubectl -n tailscale get secret operator-oauth
kubectl -n tailscale get pods
kubectl -n tailscale get proxygroup traefik-ingress-proxies
kubectl -n kube-system get service traefik-tailscale-ha
```

The routing resources use Argo CD sync wave `1`, allowing the chart's CRDs and
operator resources to render ahead of the `ProxyGroup` and LoadBalancer
Service during a single Application sync.

## Traffic path

```text
Tailnet client
  -> Tailscale Service VIP
  -> one of the ProxyGroup replicas
  -> kube-system/traefik-tailscale-ha
  -> Traefik pods
  -> Ingress or TCP route
  -> workload Service and Pods
```

A standalone Tailscale ingress normally uses one proxy. This repository's
`ProxyGroup/traefik-ingress-proxies` requests three ingress proxy replicas and
binds the Traefik-facing LoadBalancer Service to that group.

## K3s Traefik configuration

The packaged K3s Traefik chart is still configured on the K3s server through
`/var/lib/rancher/k3s/server/manifests/traefik-config.yaml`. That host-level
bootstrap file is outside this repository's Argo CD ownership boundary.

```yaml
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: traefik
  namespace: kube-system
spec:
  valuesContent: |-
    service:
      spec:
        type: ClusterIP

    deployment:
      replicas: 3

    ports:
      postgres:
        port: 5432
        expose:
          default: true
        exposedPort: 5432
        protocol: TCP

    providers:
      kubernetesIngress:
        publishedService:
          enabled: true
          pathOverride: kube-system/traefik-tailscale-ha
```

This keeps Traefik itself on a ClusterIP while Tailscale provides the private
Tailnet-facing LoadBalancer address.