# node_exporter role

Reusable host-exporter tasks. The calling playbook chooses hosts, sudo and rollout
order. This role reads platform/service facts, reuses a recognized systemd
exporter or installs the Debian-family package, then verifies its endpoint.
K3s nodes use the same host service. A healthy endpoint without a recognized
running systemd exporter fails instead of reusing a DaemonSet/container.

| Input | Role default | This lab supplies |
| --- | --- | --- |
| `node_exporter_listen_address` | Empty; a private IPv4 is required | Machine address from inventory |
| `node_exporter_port` | 9100 | Same |
| `node_exporter_verify_from` | Empty; no additional machine probe | `tantrum` inventory name |
| Package/service/binary | Distro Node Exporter | Same |

Configure inputs in inventory or the calling playbook. Do not edit role defaults
to store a particular VM's address or credentials. This role requires SSH/sudo
access from the playbook; it does not create that access.

```text
tasks/main.yml       detect and choose reuse/install
  → tasks/install.yml  package + listener file, when needed
  → handlers/main.yml  restart only if the managed listener file changed
  → tasks/verify.yml   local metrics + optional monitoring-machine check
```

`templates/listen.conf.j2` becomes the managed systemd listener file.
`defaults/main.yml` supplies overridable inputs. No `vars/`, `files/` or `meta/`
folder is needed for this role's current behavior.

Before installing or starting a stopped service, the metrics port must be free.
The role never deletes cluster resources; follow the
[DaemonSet migration guide](../../playbooks/node-exporter/MIGRATION.md) first.

Use [the host-selecting playbook](../../playbooks/node-exporter/main.yml) and
[manual run guide](../../playbooks/node-exporter/README.md).
The repository's `ansible.cfg` makes this shared role discoverable from nested playbooks.

The role is local source code, not a published Galaxy package. It can be reused
by other playbooks now; publishing it later needs its own metadata, versioning
and license decision. Runtime installation/idempotence still need a manual host trial.
