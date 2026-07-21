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
kube-system/traefik-tailscale-ha
LoadBalancer class tailscale
        │
        ▼
Traefik pods with HA
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


*kube-system/traefik-tailscale-ha act as a LB in your tailnet, like metallb (but for LAN)

```
