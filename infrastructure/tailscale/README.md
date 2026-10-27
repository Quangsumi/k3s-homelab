```
*note: this is installing through Helm, can move this to ArgoCD manage
```

```
kubectl apply -f 01-tailscale-auth.yaml
```
# OAuth credentials
```
helm repo add tailscale https://pkgs.tailscale.com/helmcharts
helm repo update

helm upgrade --install tailscale-operator tailscale/tailscale-operator \
  --namespace=tailscale \
  --create-namespace \
  --set-string oauth.clientId=[your-client-id] \
  --set-string oauth.clientSecret=[your-client-secret] \
  --wait

helm repo update

helm upgrade tailscale-operator \
  tailscale/tailscale-operator \
  --kubeconfig /etc/rancher/k3s/k3s.yaml \
  -n tailscale \
  -f tailscale-values.yaml
```
# Usage
```
apply this ingress, tailscale will give this service a tailscale domain
funnel: "false" (default): access through the tailscle-only domain given by tailscale
funnel true: access through the public domain also given by tailscale

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-kuma
  namespace: uptime-kuma
  annotations:
    tailscale.com/funnel: "true" # public to internet
spec:
  ingressClassName: tailscale
  defaultBackend:
    service:
      name: uptime-kuma
      port:
        number: 80
  tls:
    - hosts:
        - uptime-kuma
```

The `operator-oauth` Secret must exist before syncing `Application/tailscale`.
The chart mounts it through `oauthSecretVolume`; the secret values are not
passed through Argo CD Helm parameters.

## Tailnet prerequisites

or refere to ../traefik/10-resource-config.yaml

```