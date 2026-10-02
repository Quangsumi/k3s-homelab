```
Laptop
  |
  | kubectl -> https://192.168.63.69:6443
  v
kube-vip VIP
  |
  v
one healthy control-plane API server
  |
  v
Kubernetes API
```

### 192.168.63.69 is not permanently assigned to one VM. It is a movable IP.
```
tombstone
  kube-vip pod
  VIP owner = YES
  interface:
    192.168.63.20
    192.168.63.69  <-- virtual IP

valkyrie
  kube-vip pod
  VIP owner = NO
  interface:
    192.168.63.22

whyachi
  kube-vip pod
  VIP owner = NO
  interface:
    192.168.63.21
```

### tsl-san
1/ k3s control plane add tls-san for 192.168.63.69
```
cat /etc/rancher/k3s/config.yaml
write-kubeconfig-mode: "0644"
kube-apiserver-arg:
  - "oidc-issuer-url=https://auth.lab/realms/homelab"
  - "oidc-client-id=k3s-client"
  - "oidc-username-claim=preferred_username"
  - "oidc-username-prefix=oidc:"
  - "oidc-groups-claim=groups"
  - "oidc-groups-prefix=oidc:"
  - "oidc-ca-file=/etc/rancher/k3s/certs/rpivn-caddy.crt"
tls-san:
  - "192.168.63.69"
  - "kube-vip.lab"
```
"When generating the Kubernetes API server certificate, also include 192.168.63.69 as a valid identity."
Then the certificate contains:
```
Subject Alternative Names:

IP: 127.0.0.1
IP: 192.168.63.20
IP: 192.168.63.21
IP: 192.168.63.22
IP: 192.168.63.69    <-- added by tls-san
DNS: kubernetes
DNS: kubernetes.default
...
```

2/ laptop connect to https://192.168.63.69:6443

3/ api server send cert for https://192.168.63.69

4/ laptop check cert if it's valid for 192.168.63.69 based on kubeconfig

If you configured only kube-vip:
192.168.63.69 exists
traffic reaches API server
but TLS may reject it

If you configured only tls-san:
certificate accepts 192.168.63.69
but nobody owns 192.168.63.69
so connection fails