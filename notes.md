# Join cluster + schedualable with Longhorn
```
sudo apt install -y open-iscsi nfs-common
sudo systemctl restart k3s-agent

curl -sfL https://get.k3s.io | K3S_URL=https://192.168.63.102:6443 K3S_TOKEN=K10004b057c1607ab9c71f0e09d906ff591fb4e4a7594e0108ff251a98b4a44ab78::server:3b3c7ffdbb5b6c010556b7f5b2369903 sh -

curl -sfL https://get.k3s.io | sh -s - server --token K10299eadbcc120bb2aa44e6adcb1b3c7a1a91e90f08848a799663c73901f8ada85::server:86bedc7ec4983e566c4c352bb359da2b --server https://192.168.63.102:6443
```

```
netsh interface portproxy add v4tov4 listenaddress=192.168.63.101 listenport=6443 connectaddress=172.18.10.95 connectport=6443
sudo du -h --max-depth=2 /var/lib | sort -h | tail -30

sudo kubectl -n litellm-stack port-forward svc/prometheus 9090:9090 --address 0.0.0.0
```

- CPU/memory/probes/image/env/args: `update manifest → kubectl apply -k . → rollout happens`
- ConfigMap/Secret content: `apply → rollout restart the affected app`

- StatefulSet storage template shrink/change: `scale down → delete StatefulSet/PVC if losing data is okay → apply again`
```
sudo kubectl -n litellm-stack scale statefulset prometheus --replicas=0
sudo kubectl -n litellm-stack scale statefulset postgres --replicas=0
sudo kubectl -n litellm-stack scale deploy litellm --replicas=0
sudo kubectl -n litellm-stack scale deploy postgres-exporter --replicas=0

sudo kubectl -n litellm-stack delete statefulset prometheus
sudo kubectl -n litellm-stack delete statefulset postgres

sudo kubectl -n litellm-stack delete pvc prometheus-data-prometheus-0
sudo kubectl -n litellm-stack delete pvc postgres-data-postgres-0
```

```
sudo kubectl -n litellm-stack get deploy,statefulset,svc,pods
sudo kubectl -n litellm-stack logs litellm-5474845549-7s6fb -c litellm --previous --tail=200
sudo kubectl -n litellm-stack logs litellm-5474845549-7s6fb -c litellm --tail=200
sudo kubectl -n litellm-stack rollout restart statefulset postgres
sudo kubectl -n uptime-kuma rollout restart deploy uptime-kuma
```

```
sudo kubectl -n litellm run pg-test --rm -it --restart=Never \
  --image=postgres:16-alpine \
  -- sh

pg_isready -h postgres.dev-db.svc.cluster.local -p 5432
```

# after reboot Pi
```
DISPLAY=:0 nohup firefox --kiosk https://pi-dashboard.tailee75a4.ts.net --safe-mode &

firefox --kiosk https://pi-dashboard.tailee75a4.ts.net --safe-mode

chromium \
  --kiosk \
  --app="http://192.168.63.202/" \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=Translate \
  --overscroll-history-navigation=0

```

```
K8s Dashboard
sudo kubectl -n kubernetes-dashboard create token admin-user --duration 24h
sudo kubectl -n kubernetes-dashboard create token dashboard-admin --duration 24h

ArgoCD Dashboard
admin
sudo kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

# Safely turn off worker nodes
```
sudo kubectl drain winterfall --ignore-daemonsets --delete-emptydir-data
kubectl uncordon winterfall
```


```
cat /proc/sys/vm/swappiness
sudo sysctl vm.swappiness=30

free -m
sudo swapoff -a
free -m
swapon -a 
```