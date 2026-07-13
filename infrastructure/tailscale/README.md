```
kubectl create namespace tailscale
```

`tailscale-auth.yaml`
```
apiVersion: v1
kind: Secret
metadata:
  name: tailscale-auth
  namespace: tailscale
stringData:
  TS_AUTHKEY: tskey-auth-xxx
```

```
kubectl apply -f tailscale-auth.yaml
```


`OAuth credentials`
```
Client ID: xxx
Client Secret: tskey-client-xxx
```
```
helm repo add tailscale https://pkgs.tailscale.com/helmcharts
helm repo update

helm upgrade --install tailscale-operator tailscale/tailscale-operator \
  --namespace=tailscale \
  --create-namespace \
  --set-string oauth.clientId=your-client-id \
  --set-string oauth.clientSecret=your-client-secret \
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

```
Open postgres port in Traefik
Save it. K3s will automatically reconcile the packaged Traefik chart.

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
        type: ClusterIP

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
          pathOverride: kube-system/traefik-tailscale
```