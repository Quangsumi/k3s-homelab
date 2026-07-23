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
