# POD LEVEL
ServiceAccount gives a pod an identity when that pod calls the Kubernetes API  
Pod -> ServiceAccount token -> API server -> RBAC  
**For a pod that does not call the Kubernetes API:**
```
apiVersion: v1
kind: ServiceAccount
metadata:
  name: litellm
  namespace: litellm
automountServiceAccountToken: false

---
# Inside the LiteLLM Deployment:
spec:
  template:
    spec:
      serviceAccountName: litellm
      automountServiceAccountToken: false
```
**For a pod that needs the API:**
```
spec:
  template:
    spec:
      serviceAccountName: prometheus # Token mounting remains enabled

Then create:
ServiceAccount prometheus
        +
Role: get/list/watch pods and services
        +
RoleBinding: give that Role to prometheus
```

# kubectl LEVEL
Human kubectl -> user identity -> API server -> RBAC  
### 1/ Client certificate
```
Alice's kubeconfig
  ├── cluster address and public CA
  ├── Alice's private key
  └── certificate saying CN=alice (username=alice)
                 │
                 ▼
API identifies user as "alice"
                 │
                 ▼
RoleBinding grants alice access

- Generate alice.key, use Root CA to sign alice.crt, Create RBAC/RoleBinding for alice, give Alice kubeconfig that include .key/.crt,
- The Root CA is installed when k3s is installed
- Cons: 100 employess, need to generate 100 certs, need to distribute/rotate/revoke/... each of them -> hard to manange
```
Bind Alice identity with roles
```
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alice-view
  namespace: monitoring
subjects:
  - kind: User
    name: alice  # alice's kubeconfig will include this identity, k3s server will check what permission this identity have when she perform kubectl
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: view
  apiGroup: rbac.authorization.k8s.io
```

### 2/ OIDC provider
```
kubectl talk to Authentik/Keycloke, k8s and k3s do not need to

Step 1
kubectl get pods
kubectl checks its kubeconfig to find "auth-provider: oidc"
or, more commonly today, an exec plugin that performs OIDC login.

Step 2
kubectl opens a browser -> https://auth.lab/login

Step 3: OIDC provider verfiy user/password, if succeed, return ID Token include user information and Sign the token

Step 4
kubectl receives the token and stores it locally
it retries kubectl get pods

Step 5
instead of sending a certificate, kubectl sends GET /api/v1/pods Bearer eyJhbGc...

Step 6
Kubernetes/API Server receives it
because Kubernetes already set to have OIDC public token, it use it to verify if JWT is signed by OIDC Issuer

Step 7
Kubernetes extracts username/group/... from JWT -> RBAC binding kick in

```

### 3/ A short-lived ServiceAccount token, mainly for temporary access or automation
Not "logging in as a user", but actually logging in as a pod
A ServiceAccount is not a human. It is an identity for a pod.

Software that manages Kubernetes gets a ServiceAccount with scoped RBAC:
ArgoCD, ESO,Cert-manager, Longhorn, Traefik, Prometheus
Needs to call https://kubernetes.default.svc (Kubernetes API) to create Deployments, update Services, watch Pods, ...
The API request is identical to OIDC (Authorization: Bearer <JWT>), but the difference is who issued the JWT
JWT token: K8s API issue/sign it, give it to ServiceAccount, then ServiceAccount can communicate with it.

Software that just runs on Kubernetes doesn't need to know Kubernetes exists and should not receive an API credential:
Litellm, Postgres, pgAdmin, Grafana, Note, Pi-dashboard

kubectl create token grafana-serviceaccount --duration=8h 
-> eyJhbGcOi... for system:serviceaccount:monitoring:grafana-serviceaccount

### 4/ Authentication Proxy or Webhook
**1/ Authentication Proxy (in front of Kubernetes)**
```
kubectl -> Authentication Proxy -> API Server -> RBAC
The proxy is responsible for: authenticating users, forwarding requests, telling Kubernetes (User = alice, Groups = developers)

eg:
kubectl GET /api/v1/pods -> Proxy -> forward X-Remote-User: alice/X-Remote-Group: developers to API Server
proxy is trusted, no doens't matter if it does what with the Header.

Tailscale API server proxy:
Tailscale Client -> Tailscale API Proxy -> API Server -> RBAC
```

**2/ Authentication Webhook (Kubernetes asks another service)**
```
Because sometimes the authentication system cannot issue OIDC tokens, No OAuth, No JWT, Just a proprietary API.
Imagine a company has
1985 -> Mainframe -> Custom Employee Database

They write a webhook:
kubectl -> Bearer Token -> API Server -> [Webhook check if token valid -> Legacy API -> Webhook response] -> RBAC
```

## Every authentication model flow:
**Client Certificate:**
```
kubectl -> Certificate -> API verifies certificate -> alice -> RBAC
```

**OIDC:**
```
kubectl -> JWT -> API verifies JWT signature -> alice -> RBAC
```

**ServiceAccount:**
```
Pod -> ServiceAccount JWT -> API verifies JWT -> system:serviceaccount:... -> RBAC
```

**Proxy:**
```
kubectl -> Proxy Login -> Proxy says alice -> API trusts proxy -> RBAC
```

**Webhook:**
```
kubectl -> Bearer Token -> API asks webhook -> Webhook replies alice -> RBAC
```