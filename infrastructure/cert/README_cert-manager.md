```
Infisical
  HOMELAB_ROOT_CA_CRT
  HOMELAB_ROOT_CA_KEY
          ↓
ESO ExternalSecret in cert-manager namespace
          ↓
Secret/homelab-ca-key-pair
          ↓
ClusterIssuer/homelab-ca
          ↓
cert-manager issues exact certificates
          ↓
argocd/argocd-lab-tls
litellm/litellm-lab-tls
...
          ↓
Traefik
```

```
helm upgrade --install cert-manager \
  oci://quay.io/jetstack/charts/cert-manager \
  --version v1.21.0 \
  --namespace cert-manager \
  --create-namespace \
  --set crds.enabled=true \
  --wait
```
### Root key is password-encrypted. cert-manager needs an unencrypted signing key for unattended operation
```
openssl pkey \
  -in homelab-root-ca.key \
  -out homelab-root-ca-online.key
```
### Verify the certificate and new key match. The two hashes must be identical.
```
openssl x509 -noout -modulus \
  -in homelab-root-ca.crt |
openssl sha256

openssl rsa -noout -modulus \
  -in homelab-root-ca-online.key |
openssl sha256
```
### Store the CA in Infisical
```
/HOMELAB_ROOT_CA_CRT
/HOMELAB_ROOT_CA_KEY
```