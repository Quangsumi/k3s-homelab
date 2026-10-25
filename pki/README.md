# Public certificate reference

Public certificates only. Host distribution uses the [Ansible certificates job](../ansible/playbooks/certificates/README.md).

## Files and consumers

```text
public/caddy-root.crt
  -> Pi rpivn-caddy.crt
  -> control planes: /etc/rancher/k3s/certs/rpivn-caddy.crt (OIDC)
  -> Kubernetes apps/ESO and ACME HTTPS trust

public/homelab-root-v1.crt + public/homelab-root-v2.crt
  -> bundles/application-trust.pem
  -> Pi homelab-root-ca.pem -> Caddy and Keycloak

public/k3s-server-ca.crt
  -> Pi k3s-ca.pem -> Caddy verifies Kubernetes API

public/proxmox-cluster-ca.crt + public/endgame-selfsigned.crt
  -> bundles/proxmox-api-trust.pem
  -> Pi proxmox-trust.pem -> Caddy verifies both Proxmox APIs
```

Pi paths are under `/home/pi/Desktop/rpivn-app/ca/`. Browser trust uses the individual Caddy and Homelab roots. Retain Homelab v1 while old certificates still require it.

## Inspect and rebuild bundles

WSL/Linux, repository root:

```bash
openssl x509 -in pki/public/caddy-root.crt -noout -subject -issuer -dates -fingerprint -sha256

cat pki/public/homelab-root-v1.crt pki/public/homelab-root-v2.crt > pki/bundles/application-trust.pem
cat pki/public/proxmox-cluster-ca.crt pki/public/endgame-selfsigned.crt > pki/bundles/proxmox-api-trust.pem

openssl crl2pkcs7 -nocrl -certfile pki/bundles/application-trust.pem | openssl pkcs7 -print_certs -noout
openssl crl2pkcs7 -nocrl -certfile pki/bundles/proxmox-api-trust.pem | openssl pkcs7 -print_certs -noout
```

Each bundle should list two certificates. Verify a replacement certificate's fingerprint against its source before distributing it.

## Kubernetes: only when Caddy's root changes

`infrastructure/cert-manager` references this folder's Kustomization, which reads `public/caddy-root.crt` directly to create `ConfigMap/caddy-root-ca`. No certificate copy is needed.

The ACME issuer still requires an embedded base64 value. PowerShell, repository root:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes((Resolve-Path .\pki\public\caddy-root.crt).Path))
```

Paste the base64 output into `spec.acme.caBundle` in `infrastructure/cert-manager/infisical-acme/05-cluster-issuer.yaml`. It authenticates **infisical.lab HTTPS**, not issued website certificates. An unchanged certificate needs no update merely because its PEM formatting differs.

```powershell
kubectl diff -k .\infrastructure\cert-manager
kubectl diff -k .\infrastructure\cert-manager\infisical-acme
```

Review all differences before your normal apply/GitOps rollout. trust-manager distributes `caddy-trust-bundle` ConfigMaps to the selected namespaces; applications keep their existing mounts and trust settings. Aspire is covered by the `monitoring` namespace.

## Reload after a trust change

On the Pi, validate Caddy first, then reload:

```bash
sudo docker exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile --force
```

Keycloak uses a single-file bind mount. Recreate it after replacing its bundle; this interrupts login:

```bash
cd /home/pi/Desktop/rpivn-app/keycloak
sudo docker compose up -d --force-recreate keycloak
```

For Kubernetes applications, reload/restart the affected process if it caches trust, then test its actual connection. Control-plane restarts require a separate one-server-at-a-time procedure. Formatting-only changes need no restart.

## Windows

After verifying the root, install only if needed. PowerShell, repository root:

```powershell
Import-Certificate -FilePath .\pki\public\homelab-root-v2.crt -CertStoreLocation Cert:\CurrentUser\Root
```

Use `caddy-root.crt` for Caddy trust. This affects the current user's Windows store; check browser-specific stores separately.

## Maintenance

- Certificate/bundle contents: this folder.
- Host addresses and users: `ansible/inventory/`.
- Remote file paths: `ansible/playbooks/certificates/main.yml`.
- Kubernetes namespaces: `infrastructure/cert-manager/10-caddy-trust-bundle.yaml`.
- Rotation order: distribute old+new trust -> reload/test -> change issuance -> retire old trust.
- Rollback: restore the previous public file or Ansible backup, then reload its consumer.
