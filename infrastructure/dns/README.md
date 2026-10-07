# Homelab DNS inside Kubernetes

CoreDNS forwards `.lab` queries directly to Pi-hole at `192.168.63.102`.
This lets in-cluster OAuth2 Proxy clients resolve `auth.lab` and its `rpivn.lab`
CNAME target consistently, independently of each node's upstream DNS settings.
Other domains retain the packaged CoreDNS configuration.

K3s CoreDNS already imports custom `*.server` files from `coredns-custom`.
Apply this standalone configuration (no Argo CD Application is registered here):

```sh
kubectl apply -f infrastructure/dns/05-coredns-custom.yaml
kubectl -n kube-system rollout restart deployment/coredns
kubectl -n kube-system rollout status deployment/coredns
```

Pi-hole must remain reachable from cluster pods on UDP and TCP port 53 and
serve authoritative local records for `.lab`; avoid forwarding `.lab` back to
CoreDNS. This file is separate from K3s's managed main CoreDNS ConfigMap.
