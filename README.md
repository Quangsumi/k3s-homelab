```
                          ┌─────────────────────┐
                          │ Pi-hole DNS          │
                          │ grafana.lab         │
                          │ → 100.70.21.100      │
                          └──────────┬──────────┘
                                     │
Laptop / Phone / Dev PC              │
on Tailscale                         │
        │                            │
        ▼                            │
http://grafana.lab                  │
        │                            │
        ▼                            │
100.70.21.100 over Tailscale ◄───────┘
        │
        ▼
kube-system/traefik-tailscale
LoadBalancer class tailscale
        │
        ▼
Traefik pod
        │
        ▼
Ingress: grafana.lab
        │
        ▼
monitoring/grafana
ClusterIP Service
        │
        ▼
Grafana pod


*kube-system/traefik-tailscale act as a LB in your tailnet
like metallb (but for LAN)

```
