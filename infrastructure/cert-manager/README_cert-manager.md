# Homelab TLS / CA quick reference

### Key and certificate basics

**Each identity has a key pair: a private key and a public key. The certificate contains the public key.**

| Item | Purpose | Secret? |
|---|---|---|
| Private key (`.key`) | Creates signatures; proves possession of the matching key | **Yes** |
| Certificate (`.crt`) | Contains the public key, identity, validity dates and issuer’s signature | No |
| CA | An authority that signs certificates | Its private key is secret |
| Leaf certificate | Identifies a website or service; normally cannot issue certificates | No |

**Two signatures to distinguish:**

- **CA signs the website certificate:** endorses the website name and public key.
- **Website signs the TLS handshake:** proves the server possesses the matching website private key.

### Common certificate chain

```text
ROOT CA
├── Root private key — secret, preferably kept offline
└── Root certificate — contains ROOT public key
    Explicitly trusted by the browser/OS
          │
          │ Root private key signs the intermediate certificate
          ▼
INTERMEDIATE CA
├── Intermediate private key — secret, used for routine issuance
└── Intermediate certificate — contains INTERMEDIATE public key
    Accepted because its signature verifies back to the trusted root
          │
          │ Intermediate private key signs the website certificate
          ▼
WEBSITE / LEAF
├── Website private key — secret, used by the TLS server
└── Website certificate — contains WEBSITE public key
    Includes permitted website names, e.g. app.homelab
```

**Signing goes downward. Certificate verification goes upward.**

The browser normally explicitly trusts the **root**. An intermediate receives authority through a valid certificate signed by that root.

### Current homelab design: root directly signs websites

**There is no intermediate in this design.**

```text
ROOT CA
├── homelab-root-ca.key
│   Passphrase-encrypted copy of the root private key
│
├── homelab-root-ca-online.key
│   Unencrypted copy of the SAME root private key
│   Available to cert-manager through Infisical
│
└── homelab-root-ca.crt
    Contains root public key
    Installed as trusted on client devices
          │
          │ Online root private key signs website certificates
          ▼
WEBSITE
├── tls.key — website's own private key
└── tls.crt — website certificate containing website public key
```

### Infisical → cert-manager → Traefik

```text
Infisical
├── HOMELAB_ROOT_CA_CRT ← homelab-root-ca.crt
└── HOMELAB_ROOT_CA_KEY ← homelab-root-ca-online.key
          │
          ▼
ESO (External Secrets Operator)
ExternalSecret in cert-manager namespace
          │
          │ Synchronizes values into:
          ▼
Secret/homelab-ca-key-pair
├── tls.crt = ROOT certificate
└── tls.key = ROOT private key
          │
          │ Referenced by:
          ▼
ClusterIssuer/homelab-ca
          │
          │ Used by cert-manager for Certificate resources
          ▼
Per-website Secrets
├── argocd/argocd-lab-tls
├── litellm/litellm-lab-tls
└── ...
          │
          │ Referenced by website ingress configuration
          ▼
Traefik
Uses website certificate + website private key for browser connections
```

| Secret entry | Meaning |
|---|---|
| `tls.crt` | Website certificate; may also include intermediate certificates |
| `tls.key` | Website private key matching the public key in `tls.crt` |
| `ca.crt` | CA information supplied by the issuer; is the root certificate `homelab-root-ca.crt` in this design |

### Browser connection flow

```text
Browser opens https://app.homelab
          │
          ▼
Traefik presents the website certificate
          │
          ▼
Browser checks:
├── Website name matches
├── Certificate dates are valid
├── Certificate signature verifies using the trusted root public key
└── Other applicable security checks pass
          │
          ▼
Traefik signs handshake proof using WEBSITE tls.key
          │
          ▼
Browser verifies proof using WEBSITE public key inside tls.crt
          │
          ▼
TLS handshake completes
Session keys encrypt HTTP traffic
```

**The root endorses the website’s identity. The website private key proves the server owns that identity.**

### Install cert-manager

```bash
helm upgrade --install cert-manager \
  oci://quay.io/jetstack/charts/cert-manager \
  --version v1.21.0 \
  --namespace cert-manager \
  --create-namespace \
  --set crds.enabled=true \
  --wait
```

### Create the unencrypted signing-key copy

**This removes storage encryption from the output copy. It preserves the underlying private key.**

```bash
openssl pkey \
  -in homelab-root-ca.key \
  -out homelab-root-ca-online.key
```

Verify both key files and the certificate match

**Expected: all three commands succeed and print the same SHA-256 fingerprint.**

```bash
# Public key derived from the encrypted root key
openssl pkey -in homelab-root-ca.key -pubout -outform DER |
  openssl dgst -sha256

# Public key derived from the online root key
openssl pkey -in homelab-root-ca-online.key -pubout -outform DER |
  openssl dgst -sha256

# Public key extracted from the root certificate
openssl x509 -in homelab-root-ca.crt -pubkey -noout |
  openssl pkey -pubin -outform DER |
  openssl dgst -sha256
```

### Stronger design: offline root, online intermediate

Each intermediate uses a **different key pair**. Separate intermediates allow separate expiry periods, access controls, audit records and rotation schedules. Domain restrictions require explicit **name constraints**; an intermediate’s name alone does not restrict what it can sign.

```text
ROOT CA
├── Root private key — offline
└── Root certificate — trusted on client devices
          │
          │ Root signs intermediate certificates
          ├── Kubernetes Intermediate
          ├── Home Wi-Fi Intermediate
          └── Development Intermediate

KUBERNETES INTERMEDIATE
├── Intermediate private key
│   Infisical → ESO → Kubernetes → cert-manager
└── Intermediate certificate
          │
          │ Intermediate private key signs:
          ▼
Website certificates
```

### `pathlen`: certificate setting, not key setting

| Setting | Meaning |
|---|---|
| Intermediate `CA:TRUE, pathlen:0` | Can issue leaf certificates; valid paths cannot contain another intermediate below it |
| CA `CA:TRUE, pathlen:1` | Allows one intermediate level below it |
| Leaf `CA:FALSE` | Is not a certificate authority |

For the stronger design:

```text
Root certificate:         CA:TRUE, pathlen:1
                          Documents the intended one-intermediate depth*

Intermediate certificate: CA:TRUE, pathlen:0
                          Issues leaves, with no further intermediate level

Website certificate:      CA:FALSE
```

`pathlen` limits **CA depth**, not the number of website certificates or permitted domain names. It constrains certificate validation; it does not physically prevent a key from signing data.

*Trust-anchor handling varies: do not rely solely on a root certificate’s `pathlen` being enforced. Put the required constraint on the intermediate certificate.* [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280.html#section-4.2.1.9)
