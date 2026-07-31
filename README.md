```
                          ┌─────────────────────┐
                          │ Pi-hole DNS         |
                          │ grafana.lab         │
                          │ → 100.70.21.100     │
                          └──────────┬──────────┘
                                     │
Laptop / Phone / Dev PC              │
on Tailscale                         │
        │                            │
        ▼                            │
http://grafana.lab                   │
        │                            │
        ▼                            │
100.70.21.100 over Tailscale ◄───────┘
        │
        ▼                                                      
kube-system/traefik-tailscale-ha                                
LoadBalancer class tailscale                                     
        │                                                       
        ▼                                                       
Traefik pods with HA ◄────── TLS Secret ◄────── cert-manager ◄────── ESO ◄────── Infisical
        │
        ▼
Ingress: grafana.lab
        │
        ▼
ClusterIP Service
        │
        ▼
Grafana pod ◄────── ESO ◄────── Infisical


*kube-system/traefik-tailscale-ha act as a LB in your tailnet, like metallb (but for LAN)

```

```
                Internet / LAN
                       │
                  HTTPS Request
                       │
                 Laptop / Phone
                       │
                       ▼
                 Traefik Ingress
             (presents leaf certificate)
                       ▲
                       │
                 TLS Secret
                       ▲
                       │
                 cert-manager
```

```
Grafana
     │
 HTTPS
     ▼
Keycloak (behind Caddy)
     ▲
     │
Leaf certificate signed by
Caddy Root CA

Grafana trusts
Caddy Root CA
     ▲
     │
ConfigMap
     ▲
     │
trust-manager
```
## Authentication And Logout

Keycloak at `auth.lab` is the OIDC provider. Application authorization remains
local to each application; OIDC login does not grant Kubernetes RBAC permissions.

| Application | OIDC support | Login | Logout |
| --- | --- | --- | --- |
| Argo CD | Native | Keycloak OIDC | RP-initiated logout clears the Argo CD session and the Keycloak SSO session. |
| Grafana | Native | Keycloak Generic OAuth/OIDC | RP-initiated logout clears the Grafana session and the Keycloak SSO session. |
| pgAdmin | Native | Keycloak OIDC | RP-initiated logout clears the pgAdmin session and the Keycloak SSO session. |
| LiteLLM | Native | Keycloak Generic OIDC | RP-initiated logout clears the LiteLLM session and the Keycloak SSO session. |
| Prometheus | No native OIDC | Keycloak through OAuth2 Proxy | OAuth2 Proxy RP-initiated logout at `/oauth2/sign_out`; Prometheus has no logout button. |
| Longhorn | No native OIDC | Keycloak through OAuth2 Proxy | OAuth2 Proxy RP-initiated logout at `/oauth2/sign_out`; Longhorn has no logout button. |
| PostgreSQL | No | PostgreSQL credentials and service secrets | Database connections end independently of browser and Keycloak sessions. |

None of these applications currently receives standards-compliant OIDC
front-channel or back-channel logout. Logging out clears the current application
and Keycloak sessions, but may not immediately clear sessions already open in
other applications.

The Kubernetes API accepts Keycloak OIDC tokens for `kubectl`, then applies
Kubernetes RBAC. CLI logout clears the local credential or token cache and is
separate from browser application logout.

### Generate the proper logout URL with ID-token injection for Oauth2 Proxy:
``` powershell
function Get-HomelabLogoutUrl($app) {
    $returnUrl = [uri]::EscapeDataString("https://${app}.lab/")
    $keycloak = "https://auth.lab/realms/homelab/protocol/openid-connect/logout?id_token_hint={id_token}&post_logout_redirect_uri=$returnUrl"
    $rd = [uri]::EscapeDataString($keycloak)
    "https://${app}.lab/oauth2/sign_out?rd=$rd"
}

Get-HomelabLogoutUrl "prometheus"
Get-HomelabLogoutUrl "longhorn"
```