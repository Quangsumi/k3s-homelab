Create <inventory-name>.yml here for overrides, for example valkyrie.yml.
Use exact names from inventory/hosts.yml.

VM usernames default to their inventory names. Override with:

```yaml
ansible_user: actual_username
```

Administrative jobs use sudo. Supply its password through the explicitly loaded
Vault file or --ask-become-pass. SSH-key jobs manage your own keys without sudo.

For the network job, override only settings that differ from the shared defaults:

```yaml
network_dns:
  - 192.168.63.102
network_dns_test_name: tombstone.lab
```

The current network job changes DNS only and preserves existing addressing, IPv6
and interface naming. It finds existing files itself and handles backups/apply/rollback.
Hydra is OpenMediaVault and is excluded from generic network and baseline jobs.
