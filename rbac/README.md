# OIDC RBAC

Argo CD manages the RBAC resources in this directory. K3s prefixes each
Keycloak group claim with `oidc:`, so Keycloak group `apps-admins` reaches
Kubernetes as `oidc:apps-admins`.

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
|-- argocd-app.yaml
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

References:

- [Kubernetes default roles and role aggregation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#default-roles-and-role-bindings)
- [Kubernetes RBAC good practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)

## Adding a namespace

Until namespace-label generation is introduced:

1. Add one file under `namespace/apps` or `namespace/infrastructure` containing
   RoleBindings to the built-in `admin` and `view` ClusterRoles.
2. Add that file to the directory's `kustomization.yaml`.
3. Render the complete tree with `kubectl kustomize rbac` before committing.
4. Verify the intended group with `kubectl auth can-i --as-group=...` checks.

Do not create a namespace wildcard Role. The built-in roles are the baseline;
small exceptions should describe the actual missing permission.