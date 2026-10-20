# Vault: load it only when needed

The encrypted file is `secrets/vault.yml`. It is no longer automatically loaded
from group_vars/all/. Its contents and password did not change when it was moved.

**Key-only run: no Vault flags.**

```bash
ansible-playbook playbooks/ssh-keys.yml --limit huge
```

**Password bootstrap: explicitly load Vault and enable saved SSH passwords.**

```bash
ansible-playbook playbooks/ssh-keys.yml --limit huge -e @secrets/vault.yml --ask-vault-pass -e bootstrap_password_auth=true
```

**Saved sudo passwords: load Vault, but leave SSH on keys.**

```bash
ansible-playbook playbooks/baseline.yml --limit huge -e @secrets/vault.yml --ask-vault-pass --check
```

`-e @secrets/vault.yml` is Ansible's built-in option to load variables from that
file. `--ask-vault-pass` supplies its decryption password. No custom loading code
or extra switch is needed. Root-access jobs use these same two options for hashes.

To edit the encrypted file:

```bash
EDITOR=nano ansible-vault edit secrets/vault.yml
```
