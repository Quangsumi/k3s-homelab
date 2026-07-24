```
Connection 1                         Connection 2

Laptop ═════ HTTPS ═════> Traefik ═════ HTTPS/HTTP ═════> Pi/Proxmox
        certificate A                         certificate B

Connection 1: install Root CA on laptop/phone
Connection 2: Disable traefik verification, configure Traefik to trust the Proxmox/Pi apps CA

```

```
A selectorless Service has no Pods for Kubernetes to discover. Therefore, you manually provide its real destination like EndpointSlice: 192.168.63.10:8006

Traefik
   │
   │ Reads Service and EndpointSlice
   ▼
192.168.63.10:8006
   │
   ▼
Application on Pi
```

### Endpoints object
```
This API became inefficient for Services with many Pods because every endpoint was stored and updated in one large object. The Endpoints API is deprecated in Kubernetes 1.33 and late

apiVersion: v1
kind: Endpoints
metadata:
  name: web
subsets:
  - addresses:
      - ip: 10.42.1.10
      - ip: 10.42.2.15
    ports:
      - port: 8080
```

### EndpointSlice objects
```
EndpointSlice divides the backends into smaller groups It also records more information: IP address, Port, Ready or not ready, Serving or not serving, Terminating, Node and zone information, IPv4 or IPv6

Service: pi-dashboard

EndpointSlice pi-dashboard-abc:
  10.42.1.10:8080
  10.42.2.15:8080

EndpointSlice pi-dashboard-def:
  10.42.3.20:8080
  10.42.4.25:8080
```

```
Service/ClusterIP: stable IP, nochage ----> Endpoints/EndpointSlice: pod IPs, external IPs

Client/other Pods
    │
    │ Connect to 10.43.20.50:80
    ▼
Service ClusterIP
10.43.20.50:80
    │
    │ Service networking selects one endpoint
    ▼
10.42.2.15:8080
    │
    ▼
Application Pod
```