# Kanboard

Single-replica Kanboard using the official versioned image, SQLite, a 3 GiB
Longhorn PVC, and the existing Traefik/cert-manager ingress convention.
The PVC stores the database and uploaded attachments under `/var/www/app/data`.
Keep one replica and `Recreate` for SQLite. Back up this volume before upgrades.
Plugin installation through the UI is disabled; SMTP and SSO are not configured.
The official image's startup services include the scheduled Kanboard job.

## Access from a phone or laptop

Open **https://kanboard.lab/** while connected to the homelab Tailscale network,
including when away from home. This uses the existing shared Traefik Tailscale
LoadBalancer; no new public tunnel or router port forwarding is required.

1. Add `kanboard.lab` to Pi-hole's local DNS records, pointing to the current
   Tailscale address of `kube-system/traefik-tailscale-ha`. Find it with:
   `kubectl -n kube-system get service traefik-tailscale-ha -o wide`.
   Do not assume the historical address in the root README is still current.
2. Ensure phone/laptop Tailscale DNS settings use the homelab resolver for `.lab`
   and that tailnet access rules allow the Traefik endpoint on TCP 443.
3. Trust the existing homelab root CA on each client, as for the other `.lab` apps.
4. On a fresh installation, log in using Kanboard's initial `admin` / `admin`
   credentials and immediately change the administrator password.

This ingress provides remote access through Tailscale; it does not make Kanboard
public on the internet. Public access needs a separate Funnel ingress or a public
domain/ingress configuration, and administrator initialization before publication.

## Review and deployment

The files are left uncommitted for review. Argo CD reads GitHub `main`, so creating
the Application before these files reach that branch cannot deploy the local files.
The Application intentionally has manual sync, matching neighboring apps.

After review, deploy the local manifests directly if you want to keep them uncommitted:

```powershell
kubectl kustomize apps/kanboard
kubectl apply --dry-run=server -k apps/kanboard
kubectl apply -k apps/kanboard
kubectl -n kanboard rollout status deployment/kanboard --timeout=300s
kubectl -n kanboard get pods,pvc,service,ingress,certificate
```

For GitOps after the files are available on remote `main`:

```powershell
kubectl apply -f apps/kanboard/argocd-app.yaml
```

Sync `kanboard` in Argo CD, then confirm the PVC is Bound, the Deployment is Ready,
the certificate is Ready, and login works from a phone/laptop outside the LAN.

Sources: [official Docker documentation](https://docs.kanboard.org/v1/admin/docker/)
and [pinned release](https://github.com/kanboard/kanboard/releases/tag/v1.2.54).
