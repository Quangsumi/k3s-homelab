# Copy public trust certificates

Uses the existing host inventory. File mappings are in [main.yml](main.yml); certificate contents and reload commands are in [pki/README.md](../../../pki/README.md).

## Preview

WSL/Linux, from `ansible/`:

```bash
source ~/.venvs/homelab-ansible/bin/activate
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
ansible-playbook playbooks/certificates/main.yml --syntax-check
ansible-playbook playbooks/certificates/main.yml --limit rpivn --list-hosts
ansible-playbook playbooks/certificates/main.yml --limit rpivn --check --diff
```

Expected: one host and four Pi file destinations. Existing directories and SSH access are required.

## Copy

After reviewing the preview:

```bash
ansible-playbook playbooks/certificates/main.yml --limit rpivn --diff
```

For a control plane, preview and copy separately:

```bash
ansible-playbook playbooks/certificates/main.yml --limit tombstone --check --diff --ask-become-pass
ansible-playbook playbooks/certificates/main.yml --limit tombstone --diff --ask-become-pass
```

Replace `tombstone` with `whyachi` or `biteforce`; omit the password prompt where sudo is passwordless. Existing vault options also work.

Exactly one host is required. Changed file contents are backed up; no services restart and no Kubernetes resources change. Test the affected connection after any needed manual reload.

## Tantrum monitoring

Ansible combines the Homelab application roots and Rpivn Caddy root from
`pki/` into `shared/trust/outbound-ca-bundle.pem` in the existing
`/home/tantrum/tantrum-monitoring` checkout. Containers use it to verify
outbound HTTPS. Browsers and agents verify Tantrum HTTPS using Tantrum's Caddy
root.

From `ansible/`, preview the update and then publish the bundle:

```bash
ansible-playbook playbooks/certificates/main.yml --limit tantrum --check --diff --ask-become-pass
ansible-playbook playbooks/certificates/main.yml --limit tantrum --diff --ask-become-pass
```

Omit `--ask-become-pass` if sudo is passwordless. Recreate any consuming
containers that need to reload the CA file after an update.
