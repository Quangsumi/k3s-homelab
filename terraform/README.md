# Terraform for the home lab

Each Keycloak configuration has its own plan and state. Coder uses Terraform
to build workspaces from the template you publish to Coder.

| Configuration | What it creates |
| --- | --- |
| [Password and a second factor](keycloak/mfa-browser/README.md) | One sign-in flow that requires a password and either an authenticator app code or a security key. |
| [Guest access for one app](keycloak/guest-access/README.md) | A guest realm, an app sign-in client, a viewer group, and invitation-only GitHub linking. |
| [Coder workspace template](coder/homelab-multi-repo-template/README.md) | The multi-repository workspace template published to Coder. |

Add future independent changes under `terraform/<system>/<change>/` with their
own guide and state. Keep the state between runs. It records what Terraform
created and can contain secrets. Keep any saved plans and state files private.

## Connect Terraform to Keycloak

Install Terraform 1.9 or later. Run it from a machine that can reach Keycloak
and trusts the certificate for `auth.lab`.

In the realm specified by the configuration's guide, create an OpenID Connect
client for Terraform. Turn on **Client authentication** and **Service accounts
roles**. Turn off **Standard flow** and **Direct access grants**. Assign the
role listed in the guide under **Service accounts roles**. Copy the client
secret from **Credentials** into the terminal prompt below.

```bash
export KEYCLOAK_CLIENT_ID=keycloak-terraform # Name of the client in the guide's realm.
read -rsp 'Keycloak client secret ' KEYCLOAK_CLIENT_SECRET # Read it without echoing it.
export KEYCLOAK_CLIENT_SECRET
printf '\n'
```

[Keycloak Terraform provider authentication](https://registry.terraform.io/providers/keycloak/keycloak/latest/docs)
