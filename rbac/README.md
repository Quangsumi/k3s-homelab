# OIDC RBAC

K3s prefixes Keycloak group claim with `oidc:`, so Keycloak group `apps-admins` reaches Kubernetes as `oidc:apps-admins`.

## OIDC authentication flow

```text
1. Laptop OIDC plugin --HTTPS--> Caddy --HTTP(S)--> Keycloak
   Trust: C:\Users\<user>\.kube\rpivn-caddy.crt

2. Laptop kubectl --HTTPS + bearer token--> K3s API server
   Trust: K3s API CA from kubeconfig "- cluster: certificate-authority-data:< xxx > "

3. K3s API server --HTTPS--> Caddy --HTTP(S)--> Keycloak discovery and JWKS
   Trust: /etc/rancher/k3s/certs/rpivn-caddy.crt
```

The complete request flow is:

1. The `kubectl oidc-login` plugin connects to `https://auth.lab` through
   Caddy. The plugin validates Caddy's TLS certificate using the
   `rpivn-caddy.crt` file on the laptop.
2. The browser completes the login with Keycloak. The browser must trust the
   same CA through the Windows or browser trust store.
3. Keycloak returns an ID token signed with the realm's signing key.
4. `kubectl` connects to the K3s API server. This is a different TLS
   connection, validated with the K3s API CA stored in the kubeconfig.
5. `kubectl` sends the ID token to the API server as a bearer token.
6. Each K3s API server retrieves Keycloak's discovery document and public JWT
   signing keys through Caddy. It validates that HTTPS connection with its
   local copy of `rpivn-caddy.crt`.
7. The API server verifies the token signature, issuer, audience, expiration,
   username claim, and group claims.
8. Kubernetes RBAC evaluates the resulting `oidc:<username>` and
   `oidc:<group>` identities.

### OIDC configuration on K3s servers

On every `server node` (`agent node` don't need this):

```yaml
kube-apiserver-arg:
  - "oidc-issuer-url=https://auth.lab/realms/homelab"
  - "oidc-client-id=k3s-client"
  - "oidc-username-claim=preferred_username"
  - "oidc-username-prefix=oidc:"
  - "oidc-groups-claim=groups"
  - "oidc-groups-prefix=oidc:"
  - "oidc-ca-file=/etc/rancher/k3s/certs/rpivn-caddy.crt"
```

The laptop OIDC plugin configuration must use the same issuer and client ID:

```text
--oidc-issuer-url=https://auth.lab/realms/homelab
--oidc-client-id=k3s-client
--certificate-authority=C:\Users\<user>\.kube\rpivn-caddy.crt
```

### Certificate meanings

| Certificate or key | Stored or presented by | Purpose |
| --- | --- | --- |
| `rpivn-caddy.crt` | Laptop and every K3s server | Public CA certificate used to trust the TLS certificate Caddy presents for `auth.lab` |
| Caddy `auth.lab` leaf certificate | Caddy only | Proves that the HTTPS endpoint is `auth.lab`; it is signed by the CA represented by `rpivn-caddy.crt` |
| K3s API CA | Laptop kubeconfig as `certificate-authority-data` or `certificate-authority` | Allows `kubectl` to verify the K3s API server's TLS certificate |

## Layout

```text
rbac/
|-- cluster/
|   |-- global/          # Cluster-wide administrators and viewers
|   |-- apps/            # Narrow cluster-scoped application exceptions
|   `-- infrastructure/  # Narrow cluster-scoped infrastructure exceptions
|-- namespace/
|   |-- apps/            # RoleBindings for application namespaces
|   `-- infrastructure/  # RoleBindings for infrastructure namespaces
`-- kustomization.yaml
```
The `cluster/apps` and `cluster/infrastructure` directories are intentionally
empty. Add resources there only when a group needs direct `kubectl` access to a
specific cluster-scoped API. Normal infrastructure changes should follow this
path:

```text
infrastructure admin -> Git -> Argo CD -> Kubernetes API
```

## Access model

| Keycloak group | Kubernetes role | Scope |
| --- | --- | --- |
| `cluster-admins` | built-in `cluster-admin` | Entire cluster |
| `cluster-viewers` | built-in `view` | Every namespace, within `view` limits |
| `apps-admins` | built-in `admin` | Listed application namespaces |
| `apps-viewers` | built-in `view` | Listed application namespaces |
| `infrastructure-admins` | built-in `admin` | Listed infrastructure namespaces |
| `infrastructure-viewers` | built-in `view` | Listed infrastructure namespaces |

Using the built-in roles avoids maintaining lists of API groups and resources.
The only custom Role is the deliberately restricted `kube-system` permission
for the `traefik-tailscale-ha` Service.

## Important limitations

The built-in `view` role is a safe baseline, not a promise that a user can read
every API resource installed in the cluster. In particular:

- `view` does not permit reading Secret values or changing RBAC.
- A new CRD may not be visible through `view` unless its operator supplies a
  ClusterRole aggregated into the built-in role.
- The built-in `admin` role may have the same CRD limitation. Argo CD should
  apply those resources when direct human access is unnecessary.
- Wildcard rules such as `apiGroups: ["*"]` and `resources: ["*"]` are not used.
  They silently grant access to future APIs and can include sensitive resources
  or subresources that are more powerful than their HTTP verb suggests.
- Native Kubernetes RBAC cannot select namespaces by label. A RoleBinding must
  exist in every namespace where a group receives `admin` or `view`.

When a CRD needs direct human access, first check whether its chart provides an
aggregated `admin` or `view` role. Otherwise add the smallest possible exception
under `cluster/apps` or `cluster/infrastructure`; do not build a catch-all CRD
inventory role.

If the per-namespace RoleBinding files become burdensome, introduce a policy
controller such as Kyverno as a separate, reviewed change. It can generate the
bindings from namespace labels, but it adds another cluster controller and is
therefore not bundled into this RBAC refactor.

## Adding a namespace

Until namespace-label generation is introduced:

1. Add one file under `namespace/apps` or `namespace/infrastructure` containing
   RoleBindings to the built-in `admin` and `view` ClusterRoles.
2. Add that file to the directory's `kustomization.yaml`.
3. Render the complete tree with `kubectl kustomize rbac` before committing.
4. Verify the intended group with `kubectl auth can-i --as-group=...` checks.

Do not create a namespace wildcard Role. The built-in roles are the baseline;
small exceptions should describe the actual missing permission.