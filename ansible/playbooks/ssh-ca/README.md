# SSH CA trust and principal mappings

First deploy [Step CA and Keycloak on the Pi](https://github.com/Quangsumi/rpivn-app/blob/main/step-ca/README.md)
and [configure your workstation](https://github.com/Quangsumi/rpivn-app/blob/main/step-ca/docs/clients.md).
The shared service is `https://ca.lab` through Pi Caddy; Step preserves the
existing Homelab signing chain and publishes no host port.
Infisical remains the vault; this playbook does not switch website issuers.
Run the commands below from this repository's `ansible/` directory in WSL/Ubuntu.

## 1. Review targets and trust

The playbook targets Debian/Ubuntu systemd guests in `linux_vms:!nas_appliances`:
tombstone, whyachi, biteforce, huge, minotaur, valkyrie and tantrum.
Hydra, Proxmox hosts and the Pi are excluded. Add missing VMs explicitly.

Copy the **SSH user CA public key** from the CA import workstation into
`playbooks/ssh-ca/files/ssh_user_ca_key.pub`. Compare its fingerprint with your
verified CA fingerprint record:

```sh
ssh-keygen -lf playbooks/ssh-ca/files/ssh_user_ca_key.pub
```

Never copy a private key, laptop key or X.509 root into that location.

Edit [inventory/group_vars/all/ssh-ca.yml](../../inventory/group_vars/all/ssh-ca.yml).
Replace example principal `quang` with the administrator-assigned Keycloak value.
Each host contains existing Linux account names and their complete principal allowlist:

```yaml
ssh_ca_principal_map_by_host:
  tombstone:
    tombstone: [quang]
  tantrum:
    tantrum: [quang]
```

Principal `quang` may log in as `tombstone` on tombstone and `tantrum` on tantrum.
Root mappings are rejected. Users, sudo, passwords and existing authorized_keys
are unchanged. Other certificate trust policies require manual integration.

## 2. Create temporary verification credentials

Keep your normal administration key and console available. The verifier disables
agents and prompts, so create a separate temporary key with an empty passphrase.
Use a new path; **never install its raw public key on a VM**:

```sh
umask 077
ssh-keygen -t ed25519 -N '' -f "$HOME/.ssh/ssh-ca-check"
step ssh certificate YOUR_VERIFIED_KEYCLOAK_EMAIL "$HOME/.ssh/ssh-ca-check.pub" \
  --sign --no-agent --provisioner keycloak-ssh --ca-url https://ca.lab \
  --root "$HOME/.config/homelab/rpivn-caddy.crt" --not-after 1h --force
```

Create a local YAML file outside Git, e.g. `~/.config/homelab/ssh-ca-rollout.yml`.
Use actual absolute controller paths:

```yaml
ssh_ca_rollout_enabled: true
ssh_ca_identity_reviewed: true
ssh_ca_test_private_key: /home/YOUR_USER/.ssh/ssh-ca-check
ssh_ca_test_certificate: /home/YOUR_USER/.ssh/ssh-ca-check-cert.pub
```

The certificate must authorize every mapped account tested in that run. Multiple
identities need suitable separate verification credentials/runs. Keep existing
Vault/become flags and host-key verification. The verifier requires direct SSH
reachability; ProxyJump needs an explicit verifier adjustment.

## 3. Enroll a canary

```sh
ansible-playbook playbooks/ssh-ca/trust.yml --limit tantrum --list-hosts
ansible-playbook playbooks/ssh-ca/trust.yml --limit tantrum \
  -e @"$HOME/.config/homelab/ssh-ca-rollout.yml" --check --diff
ansible-playbook playbooks/ssh-ca/trust.yml --limit tantrum \
  -e @"$HOME/.config/homelab/ssh-ca-rollout.yml" --diff
```

Check mode performs preflight only. A real run stages trust/mappings together,
validates `sshd -t` and effective account policy, reloads SSH, then proves a fresh
certificate connection. Ordinary validation/login failures restore the previous
config and generation. Network/power failures may require the Proxmox console.

Before extending the rollout, verify on the canary:

- Normal certificate login returns the intended Linux user and debug output shows
  `Server accepts key: ...-CERT ...`.
- The temporary key fails without its certificate. For this check, use a separate
  private-key filename with no `-cert.pub` companion and `CertificateFile=none`.
- An unmapped account is denied; a Keycloak non-member cannot obtain a certificate.
- A repeated unchanged Ansible run makes no configuration changes.
- Your retained administration key still works.

Review targets, then repeat the real command with `--limit workers` or another
chosen set. Runs are serial and stop on failure. Delete temporary verification
credentials after rollout; re-sign them if they expire during testing.

## 4. Change access or roll back

Edit inventory mappings, then use `principals.yml` with the same inputs and
canary sequence. Removed account files cannot linger in the active generation.
Do not edit generation files directly. Old generations remain for recovery.

Group removal/logout does not revoke existing certificates; future-dated
certificates are also possible upstream. Remove VM principal mappings for
immediate denial of new logins. Existing sessions remain open.

For removing the last account, or removing all trust from a VM, connect with the
retained administration key:

```sh
ansible-playbook playbooks/ssh-ca/rollback.yml --limit tantrum \
  -e ssh_ca_rollback_enabled=true --check --diff
ansible-playbook playbooks/ssh-ca/rollback.yml --limit tantrum \
  -e ssh_ca_rollback_enabled=true --diff
```

Rollback removes only the managed SSH block, validates and reloads SSH. Public
generation files remain. Verify a fresh administration-key connection afterward.
Retire old daily-use keys separately through the existing SSH-keys playbook only
after all devices pass verification and a break-glass path is tested.

Validation: Ansible syntax and seven-host inventory scope checked. Actual VM
rollout, rollback and idempotence still require your canary verification.
