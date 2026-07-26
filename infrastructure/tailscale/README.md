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
```
# Usage
```
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

apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: traefik
  namespace: kube-system
spec:
  valuesContent: |-
    service:
      spec:
        type: ClusterIP  # override default (LB), LB is now using Tailscale. TailScale LB -> Traefik -> app pods

    deployment:
      replicas: 3  # HA with traefik-ingress-proxies

    ports:
      postgres:         # Open postgres port in Traefik. Save it. K3s will automatically reconcile the packaged Traefik chart.
        port: 5432
        expose:
          default: true
        exposedPort: 5432
        protocol: TCP

    providers:
      kubernetesIngress:
        publishedService:
          enabled: true
          pathOverride: kube-system/traefik-tailscale-ha  # fix ArgoCD stuck at Processing
```