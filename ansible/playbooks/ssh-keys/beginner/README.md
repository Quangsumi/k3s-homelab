# Optional first exercise: one VM, no Vault

Use this only if you want to learn with the smallest inventory and playbook.
The normal [SSH-key job](../README.md) already supports the whole lab.

1. Complete the [laptop setup](../../../GUIDE.md).
2. Check `hosts.yml`: existing username and Valkyrie's IP.
3. Put your public key at `keys/laptop.pub` in the project.
4. Trust the VM fingerprint as described in the shared guide.

From the `ansible` folder in WSL:

```bash
ansible-playbook -i playbooks/ssh-keys/beginner/hosts.yml playbooks/ssh-keys/beginner/main.yml --ask-pass --check
ansible-playbook -i playbooks/ssh-keys/beginner/hosts.yml playbooks/ssh-keys/beginner/main.yml --ask-pass
```

`--ask-pass` asks for Valkyrie's existing SSH password. No sudo is used.
Test from WSL with the matching private key selected:

```bash
ssh -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no valkyrie@192.168.63.22
```

A successful login confirms the key works. Repeating the playbook should report `ok`.
