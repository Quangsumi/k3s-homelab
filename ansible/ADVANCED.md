# Roles, handlers and dynamic inventory

You have now run the individual jobs. The next steps help you organize and reuse
those working instructions. They do not replace SSH, passwords, sudo or the modules
you already learned.

We will use three questions:

| Question | Feature that helps |
|---|---|
| How do I reuse the same set of tasks in several jobs? | A role |
| How do I restart a program only after its settings change? | A handler |
| How do I get the machine list from Proxmox instead of maintaining it manually? | Dynamic inventory |

Node Exporter now uses a shared role in this project. The handler demo and
Proxmox dynamic inventory below remain teaching examples; they have not been
installed on your hosts.

## 1. Roles: give a reusable job its own home

Start with [the Node Exporter roles walkthrough](ROLES.md). It follows our real
playbook, shared role folders, inventory inputs and restart handler, then explains
Galaxy packages and how other jobs could move to roles incrementally.

The entry point is still `playbooks/node-exporter/main.yml`; it calls
`roles/node_exporter`. `ansible.cfg` supplies the shared role search path.
Lab settings live in `inventory/group_vars/all/node-exporter.yml`.

## 2. Handlers: respond to a change instead of restarting every time

Imagine a program named `demo-agent`. This is a fictional service for the lesson;
your VMs do not need to have it installed.

It reads `/etc/demo-agent.conf` when it starts. You want Ansible to manage the file,
then restart the program if that file changes.

A regular task might write the file like this:

```yaml
- name: Write the demo agent settings
  ansible.builtin.template:
    src: demo-agent.conf.j2
    dest: /etc/demo-agent.conf
    owner: root
    group: root
    mode: '0644'
  notify: Restart demo agent
```

`template` makes the destination file from a source containing placeholders.
For example, the source could contain:

```text
log_level={{ demo_log_level }}
```

With `demo_log_level: info`, the resulting file contains `log_level=info`.

The new line is:

```yaml
notify: Restart demo agent
```

Read it as: **if this task changes the file, queue the handler named Restart demo agent.**

The handler could be defined in the same playbook:

```yaml
handlers:
  - name: Restart demo agent
    ansible.builtin.service:
      name: demo-agent
      state: restarted
```

The `notify` text must match the handler's name. The file task belongs under the
playbook's `tasks:` section; `handlers:` sits alongside `tasks:`, not inside it.
Both tasks need administrator permission to manage this system file/service.
If organized as a role, the handler list would instead live in `handlers/main.yml`.

Here is the sequence in a normal successful run:

```text
Render the proposed file on the laptop
             |
Compare it with the VM's existing file
             |
     +-------+-------+
     |               |
   Same           Different
     |               |
Report ok       Write the file
     |               |
No notification Queue the handler
                     |
              Other tasks continue
                     |
              Run queued handler
```

Run it three times to understand the difference:

| Run | File task result | Handler result |
|---|---|---|
| First run: file is missing | Creates the file; reports changed | Restarts demo-agent |
| Second run: settings are identical | Reports ok; no change | Does not run |
| Third run: change info to debug | Updates the file; reports changed | Restarts demo-agent |

A handler is not normally executed immediately after the task that notifies it.
In a simple play, queued handlers run after the ordinary tasks. If several tasks
notify the same handler on the same machine before that point, it runs once there.
Each machine has its own notifications: a change on Huge does not restart a service
on Minotaur.

If later tasks need the restarted program immediately, you can explicitly run the
queued handlers at that point:

```yaml
- name: Run queued handlers before continuing
  ansible.builtin.meta: flush_handlers
```

This runs all handlers currently queued for that host, not just one named handler.
Ansible can notify that handler again after the flush if another task changes something.
Also, a later failure can prevent an earlier notification from running under normal
handler behavior. A notification is not a guarantee that a restart already happened.

**Starting a service and restarting after a change are different jobs.**
Your guest-agent baseline uses `state: started` as a normal task: make sure the
service is running whenever you run the playbook. If it is stopped, that task starts
it even when no configuration changed. Moving that check into a handler would lose
that behavior. Use a restart/reload handler only for the change-dependent action.

Your SSH-key task does not need a restart handler: SSH checks authorized keys for
new connections without requiring a server restart after each key edit.
Your network job has its own backup, apply, reconnect, verify and rollback sequence.
A handler would not replace those recovery steps.

Further reading: [Ansible handlers](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_handlers.html).

## 3. Dynamic inventory: ask Proxmox for the machine list

Your current `inventory/hosts.yml` is a **static inventory**: a machine list you
edit yourself. For example, it records Biteforce's name, ID and connection address.
If you rebuild Biteforce under another ID, somebody must update that entry.

A **dynamic inventory** gets its machine records from another system when it loads.
For this lab, that system could be Proxmox.

```text
Current approach:
You edit hosts.yml -> Ansible reads your list -> Ansible connects through SSH

Possible future approach:
Ansible asks Proxmox -> Proxmox returns VM records -> Ansible builds its list
                                                  -> connects through SSH
```

The component that asks Proxmox is called an **inventory plugin**.
`community.proxmox.proxmox` is one available plugin. It supplies inventory data;
it does not install software in the VMs or grant SSH access to them.

There are two separate connections:

| Connection | Purpose | Credentials |
|---|---|---|
| Laptop -> Proxmox API | Discover machines and their details | Proxmox API credentials, such as a token |
| Laptop -> each VM through SSH | Run your tasks | That VM's login account and SSH key/password |

A working Proxmox token does not automatically let you SSH into Hydra or Biteforce.
Their existing host_vars exceptions remain useful.

A proposed source file could be named `inventory/lab.proxmox.yml`. The name must
end in `.proxmox.yml` or `.proxmox.yaml` for this plugin to recognize it.
For teaching purposes, its core could look like this:

```yaml
plugin: community.proxmox.proxmox
url: https://192.168.63.10:8006
user: ansible-inventory@pve
token_id: inventory
token_secret: "{{ lookup('ansible.builtin.env', 'PROXMOX_TOKEN_SECRET') }}"
validate_certs: true
exclude_nodes: true
compose:
  ansible_host: proxmox_name ~ '.lab'
```

This is a proposed example, not a configured inventory source. The API user/token
would need creating with permission to read the intended VM records. The laptop
would need the community.proxmox collection, its Python requirements and trust for
the Proxmox HTTPS certificate, including the connection address matching that certificate.
The token secret is read from the controller's environment rather than written into
this example. It could instead be stored encrypted, following the plugin's documentation.

`compose` means calculate a setting from the discovered data. Here, a VM named
`biteforce` gets `ansible_host: biteforce.lab`. That works only if your DNS actually
resolves that name from the laptop. VM discovery does not create DNS records.
It also does not guarantee that a guest's IP is available or that the VM is reachable.

Before replacing your current inventory, we would need to preserve these rules:

- Stable inventory names, so `host_vars/biteforce.yml` still matches Biteforce.
- Your `linux_vms`, `workers`, `control_planes` and `nas_appliances` groups.
- Which VMs belong in the automation at all; exclude templates and unrelated guests.
- Hydra's exclusions and each guest's correct SSH account/key.
- The Proxmox host entries needed by jobs that delegate work to those hosts.
- Any variables your jobs expect, such as vmid, proxmox_name and network_address.
  The plugin may expose an ID as proxmox_vmid; mapping it to vmid is a separate setting.

The example above is intentionally incomplete for that migration. In particular,
`exclude_nodes: true` leaves out Proxmox hosts and the example does not recreate your
groups. Do not replace hosts.yml with it and expect your current jobs to run unchanged.

The first test of a future configured dynamic source would be:

```bash
ansible-inventory -i inventory/lab.proxmox.yml --graph
```

Unlike displaying your static file, this command contacts Proxmox to read the list.
It does not apply a configuration change to a VM. Inspect both the group graph and
individual host variables before using that source with a playbook.
If caching is enabled, an old cached record can remain until refreshed; dynamic
does not necessarily mean every value was fetched a moment ago.

Further reading: [Proxmox inventory plugin](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_inventory.html).

## 4. Which should you learn first?

Start by turning one small, working task list into a role in a practice copy.
Next, use a handler for one ordinary service configuration and observe changed
versus unchanged runs. Adopt dynamic inventory when maintaining your machine list
becomes a real burden; seven stable VM entries can remain perfectly manageable.

Roles organize the work. Handlers respond to changes. Dynamic inventory supplies
the machines. You can use any one of them without adopting the other two.
