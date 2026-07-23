### Create the root CA private key:
```
openssl genrsa -aes256 -out homelab-root-ca.key 4096
```
### Create the root CA certificate:
```
openssl req -x509 -new -sha256 -days 3650 \
  -key homelab-root-ca.key \
  -out homelab-root-ca.crt \
  -subj "/O=Homelab/CN=Homelab Root CA" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"
```
### Create Traefik's private key and certificate request:
```
openssl genrsa -out lab-domain.key 2048

openssl req -new \
  -key lab-domain.key \
  -out lab-domain.csr \
  -subj "/O=Homelab/CN=lab domain"
```
### Create lab-domain.ext
```
nano lab-domain.ext

basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[alt_names]
DNS.1=argocd.lab
DNS.2=litellm.lab
DNS.3=longhorn.lab
DNS.4=note.lab
DNS.5=pi-dashboard.lab
DNS.6=pgadmin.lab
```
### Sign the Traefik server certificate using your root CA:
```
openssl x509 -req \
  -in lab-domain.csr \
  -CA homelab-root-ca.crt \
  -CAkey homelab-root-ca.key \
  -CAcreateserial \
  -out lab-domain.crt \
  -days 365 \
  -sha256 \
  -extfile lab-domain.ext
```
### Verify
```
openssl verify \
  -CAfile homelab-root-ca.crt \
  lab-domain.crt

openssl x509 -in lab-domain.crt \
  -noout -subject -issuer -ext subjectAltName

lab-domain.crt: OK
DNS:argocd.lab
DNS:litellm.lab
DNS:longhorn.lab
DNS:note.lab
DNS:pi-dashboard.lab
DNS:pgadmin.lab
```