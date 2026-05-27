helm repo add metallb https://metallb.github.io/metallb
helm repo update
helm install metallb metallb/metallb --namespace metallb-system --create-namespace

kubectl apply -f metallb-config/kustomization.yaml


# some Metallb issue
```
sudo ip link set wlan0 promisc on

### force advertisement on stable nodes only rpivn (exclude nodes on VM)

- add node selector to 10-l2advertisement.yaml

nodeSelectors:
    - matchLabels:
        kubernetes.io/hostname: rpivn

- delete all pods, force re-create pods again

-> result: advertisement will only happen at node rpivn

```