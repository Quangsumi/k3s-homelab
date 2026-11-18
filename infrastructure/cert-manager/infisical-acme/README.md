# Infisical ACME

```text
cert-manager -> Infisical ACME -> intermediate CA signs website certificate
     |
     v
Website TLS Secret -> Traefik
```

This base contains the enrollment ExternalSecret and `ClusterIssuer/infisical-acme`. The canary is a separate base. Neither is included in the parent Kustomization.

## Configuration

- Infisical application: `homelab-kubernetes`; profile: `homelab-kubernetes-acme`.
- CA: Homelab v2 intermediate; profile TTL: 30 days.
- Working website configuration: RSA-2048, Digital Signature, Key Encipherment, Server Auth. The policy must permit these usages and each requested DNS name.
- Directory URL and EAB KID: `05-cluster-issuer.yaml`; copy from the application's ACME enrollment UI.
- EAB HMAC: Secrets Management project `k3s-j0tn`, environment `dev`, `/tls/INFISICAL_ACME_EAB_HMAC_KEY` -> Secret `infisical-acme-eab`, key `hmacKey`.
- Keep the HMAC's unpadded base64url value; do not encode it again.
- `spec.acme.caBundle`: Caddy root for **infisical.lab HTTPS**. See [trust maintenance](../../../pki/README.md#kubernetes-only-when-caddys-root-changes).

CA private keys stay in Infisical Certificate Manager. ESO copies the enrollment credential. Keep the legacy `homelab-ca` signer until migration and rollback requirements are resolved.

## HTTP-01

```text
Infisical -> http://<website>/.well-known/acme-challenge/<token>
          -> Traefik :80 -> cert-manager solver
```

Infisical's runtime and cert-manager must resolve the hostname and reach HTTP port 80. Solver priority 10000 takes precedence over redirect priority 1000. HTTP-01 does not support wildcard issuance.

## Render and inspect

Repository root:

```bash
kubectl kustomize infrastructure/cert-manager/infisical-acme
kubectl kustomize infrastructure/cert-manager/infisical-acme/canary
kubectl -n cert-manager get externalsecret infisical-acme-eab
kubectl get clusterissuer infisical-acme
kubectl -n cert-manager get certificate infisical-acme-canary
kubectl -n cert-manager get certificaterequest,order,challenge
```

Setup order: Traefik HTTP routing -> enrollment Secret -> ACME issuer -> canary -> websites individually. Verify the certificate actually served as well as Certificate readiness. Keep website Secret names unchanged; deleting them is unnecessary for an issuer migration.

Keep Caddy's HTTPS for Infisical independent of this issuing path. Back up Infisical's database and original `ENCRYPTION_KEY` together for recovery.

## GitOps ownership

`Application/infisical-acme` is defined in
`bootstrap/homelab/applications/infisical-acme.yaml` and remains manual-sync.
The root creates its definition but does not activate the issuer. Complete the
prerequisite checks before syncing, then verify the issuer with the separate
canary before enabling consuming sites. See [bootstrap order](../../../bootstrap/README.md).
