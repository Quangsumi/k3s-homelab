
# Required dependencies: iscsi-initiator-utils (Ubuntu/Debian)
```
sudo apt-get update
sudo apt-get install -y open-iscsi
sudo systemctl enable iscsid
sudo systemctl start iscsid
sudo systemctl status iscsid

kubectl create namespace longhorn-system

helm repo add longhorn https://charts.longhorn.io
helm repo update

helm install longhorn longhorn/longhorn \
  --namespace longhorn-system \
  --set persistence.defaultClassReplicaCount=2 \
  --set defaultSettings.createDefaultDiskLabeledNodes=true \
  --set defaultSettings.storageOverProvisioningPercentage=100
```

- `defaultClassReplicaCount=2` for HA
- `storageOverProvisioningPercentage=100` allows all available storage to be provisioned (adjust based on your needs)
- `createDefaultDiskLabeledNodes=true` add this label to nodes you want to have longhorn provision storage on it


# Verify Longhorn Installation
```
kubectl get pods -n longhorn-system
kubectl get storageclass
kubectl port-forward -n longhorn-system svc/longhorn-frontend 8080:80
```

# Usage example
**Current:**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: uptime-kuma-pvc
  namespace: uptime-kuma
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 200Mi
```

**Change To:**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: uptime-kuma-pvc
  namespace: uptime-kuma
spec:
  storageClassName: longhorn
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 200Mi
```