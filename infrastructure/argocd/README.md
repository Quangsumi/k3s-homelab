## Fresh cluster

Argo CD cannot install itself into an empty cluster. Bootstrap it once with the
official Helm chart, then apply the repository root Application. Sync `homelab-bootstrap` to create the child Applications; sync the `argocd` child last so Argo CD takes over its own lifecycle:

```sh
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --version 10.1.3

kubectl apply -f bootstrap/root-application.yaml
```

- Tailscale Ingress handles HTTPS externally, configure Argo CD server to serve HTTP internally:
```
sudo kubectl -n argocd patch configmap argocd-cmd-params-cm \
  --type merge \
  -p '{"data":{"server.insecure":"true"}}'
sudo kubectl -n argocd rollout restart deploy argocd-server
```
