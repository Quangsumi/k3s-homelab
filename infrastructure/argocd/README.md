## Fresh cluster

Argo CD cannot install itself into an empty cluster. Bootstrap it once with the
official Helm chart, then register the Application so Argo CD takes over its own lifecycle:

```sh
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --version 9.5.22

kubectl apply -f argocd-app.yaml
```

```
mkdir -p ~/.kube 
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config 
chmod 600 ~/.kube/config
export KUBECONFIG=~/.kube/config
```
kubectl -n argocd get pods
kubectl -n argocd get ingress argocd-tailscale
```

- Tailscale Ingress handles HTTPS externally, configure Argo CD server to serve HTTP internally:
```
sudo kubectl -n argocd patch configmap argocd-cmd-params-cm \
  --type merge \
  -p '{"data":{"server.insecure":"true"}}'
sudo kubectl -n argocd rollout restart deploy argocd-server
```

```
kubectl -n argocd get configmap argocd-cm -o jsonpath='{.data.timeout\.reconciliation}{"\n"}{.data.timeout\.reconciliation\.jitter}'
kubectl -n argocd get configmap argocd-cm -o jsonpath='{.data.server\.insecure}'
```