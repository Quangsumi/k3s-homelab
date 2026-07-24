```
helm repo add metallb https://metallb.github.io/metallb
helm repo update
helm install metallb metallb/metallb --namespace metallb-system --create-namespace

kubectl apply -k .
```

# some Metallb issue
```
sudo ip link set wlan0 promisc on
```

# force advertisement on stable nodes only
```
1/ add node selector to 10-l2advertisement.yaml

nodeSelectors:
    - matchLabels:
        kubernetes.io/hostname: rpivn

2/ delete all pods, force re-create pods again

-> result: advertisement will only happen at node rpivn

```