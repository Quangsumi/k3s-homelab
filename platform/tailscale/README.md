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