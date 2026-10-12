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

# Clients -> Tailscale as LB -> Traefik as ClusterIP
```
Standalone:
Client -> 1 Tailscale proxy pod -> Traefik Service -> Traefik pods

ProxyGroup:
Client -> Tailscale Service VIP (virtual IP) -> one of several proxy pods -> Traefik Service -> Traefik pods
```
#### 1/ HA ingress proxies. Run multiple proxy replicas with ProxyGroup.
```
k apply -f 05-traefik-ingress-proxies.yaml
```
#### 2/ Run Tailscale as LB & bind with ProxyGroup to run multiple replicas for HA
```
k apply -f 10-traefik-tailscale-service.yaml
```
#### 3/ Config Traefik as ClusterIP
```
sudo nano /var/lib/rancher/k3s/server/manifests/traefik-config.yaml

or refere to ../traefik/10-resource-config.yaml

```