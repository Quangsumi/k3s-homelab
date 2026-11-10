## Common command pattern

| Add this | To do this |
|---|---|
| `--limit valkyrie` | Select one VM |
| `--limit valkyrie,huge` | Select several VMs |
| `--limit workers` | Select an inventory group |
| No `--limit` | Select every host allowed by that playbook |
| `-e @secrets/vault.yml --ask-vault-pass` | Load saved credentials |
| `--ask-become-pass` | Type one shared sudo password instead |
| `-e ansible_user=root` | Use root for this run, after root access is ready |
| `--syntax-check` | Check Ansible syntax without running tasks |
