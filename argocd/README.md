kubectl create namespace argocd
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install argocd argo/argo-cd \
  -n argocd \
  -f argocd-pi-values.yaml \
  --timeout 60m \
  --wait

dex.enabled=false              disables SSO/login provider, not needed if using local admin login
notifications.enabled=false    disables Slack/email/webhook notifications, not needed now
applicationSet.replicas=0      disables ApplicationSet, useful later for many apps/clusters, not needed now
global.nodeSelector            pins pods to rpivn

Or running these:
sudo kubectl -n argocd scale deploy argocd-dex-server --replicas=0
sudo kubectl -n argocd scale deploy argocd-notifications-controller --replicas=0
sudo kubectl -n argocd scale deploy argocd-applicationset-controller --replicas=0


- make background Git pulling less frequent
sudo kubectl -n argocd patch configmap argocd-cm \
  --type merge \
  -p '{"data":{"timeout.reconciliation":"15m","timeout.reconciliation.jitter":"5m"}}'
sudo kubectl -n argocd rollout restart statefulset argocd-application-controller
sudo kubectl -n argocd rollout restart deploy argocd-repo-server


- Tailscale Ingress handles HTTPS externally, configure Argo CD server to serve HTTP internally:
sudo kubectl -n argocd patch configmap argocd-cmd-params-cm \
  --type merge \
  -p '{"data":{"server.insecure":"true"}}'
sudo kubectl -n argocd rollout restart deploy argocd-server


sudo kubectl apply -f argocd-tailscale-ingress.yaml


admin
sudo kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo


kubectl -n argocd get configmap argocd-cm -o jsonpath='{.data.timeout\.reconciliation}{"\n"}{.data.timeout\.reconciliation\.jitter}'
kubectl -n argocd get configmap argocd-cm -o jsonpath='{.data.server\.insecure}'