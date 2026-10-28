# Move Fluent Bit's saved files once

**One standalone playbook. Run it yourself after reviewing the changes.**

It stops the pod collectors, copies their database and queue into
`/var/lib/fluent-bit/pods`, compares the copies, updates the paths and starts
Fluent Bit again. It keeps the original files. It does not run from any other job.

Run from the `ansible/` folder on your Linux Ansible controller:

```bash
ansible-playbook playbooks/fluent-bit-state-migration/main.yml --syntax-check
ansible-playbook playbooks/fluent-bit-state-migration/main.yml --check
```

After approval: pause automatic sync for the Argo CD **monitoring** app, wait
for any current sync to finish, then run the same command without `--check`.
All five K3s nodes must be reachable. Use your normal SSH/sudo credentials.
The job checks every node's SSH login and sudo access before stopping anything.
Each node uses its own inventory username and saved passwords. Tombstone only
runs the Kubernetes commands.

If copying fails, Ansible stops before restarting collectors. Originals remain.
An interrupted copy can be resumed with the same command. Existing copies must
match their originals; differing files cause an error instead of being overwritten.
The job accepts collectors already paused by its previous attempt. It removes
its temporary pause setting only after every node's copy passes comparison.
Do not use `--limit` or `--start-at-task`: run the whole job so all checks run.

The existing pod mount can see the new subfolder, so this job does not deploy
other manifest changes. Before restoring automatic sync, make sure Git has the
reviewed new paths. No package installation, journald or gateway changes occur.

Pod-log forwarding pauses during the copy. Applications keep writing their local
logs; Fluent Bit catches up afterward while those files remain available.
