# Redeploy StatefulSet:
```
scale down -> delete StatefulSet -> delete PVC if losing data is okay other wise PVC will be re-attached later -> apply again

sudo kubectl -n litellm-stack scale statefulset postgres --replicas=0
sudo kubectl -n litellm-stack delete statefulset postgres
sudo kubectl -n litellm-stack delete pvc postgres-data-postgres-0
```

```
cat /proc/sys/vm/swappiness
sudo sysctl vm.swappiness=30

free -m
sudo swapoff -a
free -m
swapon -a 
```

```
netsh interface portproxy add v4tov4 listenaddress=192.168.63.101 listenport=6443 connectaddress=172.18.10.95 connectport=6443
sudo du -h --max-depth=2 /var/lib | sort -h | tail -30
```