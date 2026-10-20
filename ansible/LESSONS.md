# First exercise: add your laptop key to one VM

We will use **Valkyrie only**. Leave DNS, static IPs and the guest agent for later.

The lab notes give Valkyrie's address as `192.168.63.22`. Confirm that address in
Proxmox before running this exercise. We log in as `valkyrie`, your existing VM
account. If its exact username differs, set that username in beginner/hosts.yml.
Root can stay locked. Adding a key to your own account does not need sudo.

These are instructions for you to run later. Writing them has not changed any VM.

## 1. What are we trying to change?

Today, you log into a VM by entering its password. You want it to recognize your
laptop's SSH key instead.

An SSH key has two files:

| File | What it does |
|---|---|
| Public key, ending in `.pub` | Goes onto the VM's list of allowed keys. |
| Private key, without `.pub` | Stays with your laptop and proves it owns that public key. |

We want to put your public key in this file inside Valkyrie (the usual home folder for this account):

```text
/home/valkyrie/.ssh/authorized_keys
```

You could log in and edit that file yourself. Ansible can do that job for you.
Later, it can repeat the job on every VM.

**Success means:** a new connection from your laptop works using its key, without
entering Valkyrie's password.

## 2. What does Ansible need from us?

Two files:

1. A machine list: which VM should it connect to?
2. A job file: what should it do there?

Ansible calls the machine list an **inventory** and the job file a **playbook**.

I created small versions for this exercise:

```text
beginner/hosts.yml       <- one VM
beginner/add-key.yml     <- one job: add your public key
```

You do not need the full lab settings or encrypted password file yet.
For this first VM, Ansible will ask you to type its password.

## 3. Prepare the laptop

Your laptop runs Windows. We will run Ansible in **Ubuntu inside Windows**.
That is what WSL provides.

Follow [SETUP.md](SETUP.md). It explains installation one command at a time.
Come back here when `ansible --version` works and you are in the project's `ansible` folder.

## 4. Find your laptop's public key

**Where: Windows PowerShell.**

```powershell
Get-ChildItem "$env:USERPROFILE\.ssh\*.pub"
```

This lists public key files. It does not change them.

If you see `id_ed25519.pub`, copy it into this project:

```powershell
Copy-Item "$env:USERPROFILE\.ssh\id_ed25519.pub" 'D:\OneDrive\Desktop\Side Quests\PETs\k3s-homelab\ansible\keys\laptop.pub'
```

If your key has another filename, replace `id_ed25519.pub` with that name.
We call the copy `laptop.pub` so the job always knows where to find it.
Copy only the `.pub` file into the project.

If there are no public key files, you may need to create a key:

```powershell
ssh-keygen -t ed25519
```

It asks where to save the key. Press Enter to use the suggested location if it is
unused. If it asks to overwrite a file, answer **no** and inspect that file first.
It also asks for a passphrase: that protects the private key on your laptop.
Then repeat the copy command above.

**Expected result:** `keys/laptop.pub` contains your public key.

## 5. Read the machine list

Open [beginner/hosts.yml](beginner/hosts.yml):

```yaml
all:
  hosts:
    valkyrie:
      ansible_host: 192.168.63.22
      ansible_user: valkyrie
```

Read it from the inside out:

- `ansible_host` is the address to connect to.
- `ansible_user` is the account to log in as.
- `valkyrie` is our name for this entry.
- `hosts` contains the machine entries.
- `all` is Ansible's built-in group containing every machine in this list.

This file format is called **YAML**. Spaces show which lines belong together.
Keep the indentation shown above; do not use tabs.

**Where: Ubuntu terminal, in the project's `ansible` folder.**

```bash
ansible-inventory -i beginner/hosts.yml --graph
```

`-i beginner/hosts.yml` selects our machine list.
`--graph` displays it.

**Expected result:** you see `valkyrie` once. None of your other VMs should appear.
This command reads local files; it does not connect to the VM.

## 6. Check normal SSH from Ubuntu

Before asking Ansible to connect, check that Ubuntu can connect normally.

**Where: Ubuntu terminal.**

```bash
ssh valkyrie@192.168.63.22
```

The first connection may ask whether you trust the server. Check the VM's SSH
identity before accepting. In Valkyrie's **Proxmox console**, run:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Compare its `SHA256:...` value with the ED25519 fingerprint shown by Ubuntu's SSH
command. If SSH shows a different key type, compare the matching host public key.
A fingerprint is an identifier for the VM's SSH identity. Accept when they match.

Enter Valkyrie's real password. `password06` in our discussion was an example;
it was not a password discovered from your VM.

After login, run `exit` to return to Ubuntu on your laptop.

**Expected result:** normal SSH works. Fix a failed connection before continuing.

## 7. Read the job file

Open [beginner/add-key.yml](beginner/add-key.yml). The first lines say:

```yaml
- name: Add my laptop key to Valkyrie
  hosts: valkyrie
  gather_facts: false
```

- `name` is a description Ansible prints while running.
- `hosts: valkyrie` selects the machine from our list.
- `gather_facts: false` skips collecting general VM information; this job does not need it.

Then comes the task:

```yaml
tasks:
  - name: Allow my laptop to log in as Valkyrie's user
    ansible.posix.authorized_key:
      user: "{{ ansible_user }}"
      key: "{{ lookup('ansible.builtin.file', playbook_dir ~ '/../keys/laptop.pub') }}"
      state: present
      exclusive: false
```

Read that as:

> Add the public key from laptop.pub to valkyrie's allowed keys on Valkyrie. Keep other keys too.

| Setting | Meaning |
|---|---|
| `tasks` | The list of things to do. We have one. |
| `ansible.posix.authorized_key` | The Ansible tool that manages allowed SSH keys. These tools are called **modules**. |
| `user: "{{ ansible_user }}"` | Use the login account and edit valkyrie's allowed keys. |
| `key: ...` | Read your public key file on the laptop. |
| `state: present` | Ensure that key is in the VM's file. |
| `exclusive: false` | Keep other allowed keys. |

The long `key` expression reads a file. `playbook_dir` means the folder containing
this job file. `../keys/laptop.pub` points from there to your public key.
Leave that line as written for this exercise.

## 8. Check the instructions, then preview the change

**Where: Ubuntu terminal.**

```bash
ansible-playbook -i beginner/hosts.yml beginner/add-key.yml --syntax-check
```

This checks whether Ansible can read the instructions. It does not log into Valkyrie.
A successful check does not yet prove the connection or VM settings are correct.

Now preview:

```bash
ansible-playbook -i beginner/hosts.yml beginner/add-key.yml --ask-pass --check --diff
```

The first part selects our machine list and job file. The last options mean:

- `--ask-pass`: ask you for Valkyrie's SSH password.
- `--check`: connect and predict the change without adding the key.
- `--diff`: display the proposed difference.

During this preview, `changed` means **a change would be needed**.
It does not mean the key was added.

If you see `UNREACHABLE`, Ansible could not connect. If you see `FAILED`, read that
task's error and fix it before proceeding. Some earlier `ok` lines do not cancel an error.

## 9. Add the key

**This command changes Valkyrie. Run it when you are ready for that change.**

**Where: Ubuntu terminal.**

```bash
ansible-playbook -i beginner/hosts.yml beginner/add-key.yml --ask-pass
```

We removed `--check`, so this time Ansible performs the task.
Enter Valkyrie's password at the prompt.

An example of a successful first run:

```text
valkyrie : ok=1 changed=1 unreachable=0 failed=0
```

This is an example, not output collected from your VM.

- `changed=1`: the task added or updated the key.
- `unreachable=0`: the connection worked.
- `failed=0`: no task failed.

If your key was already there, `changed=0` is also successful.

## 10. Prove that the key works

**Where: Windows PowerShell.** Open a new connection using your original private key:

```powershell
ssh -o IdentitiesOnly=yes -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -i "$env:USERPROFILE\.ssh\id_ed25519" valkyrie@192.168.63.22
```

Replace the private filename if you chose a different public key earlier.
`-i` selects your private key. `IdentitiesOnly=yes` limits which identities SSH offers.
The options ending in `=no` prevent falling back to the VM password.

If asked for the key's passphrase, that unlocks the key on your laptop.
It is different from asking for Valkyrie's login password.

**Expected result:** a new shell opens on Valkyrie without using its password.

If it fails, keep your working password access. Check that the copied public key
matches the selected private key and that both commands use the `valkyrie` account.

## 11. Run the same job again

Back in Ubuntu:

```bash
ansible-playbook -i beginner/hosts.yml beginner/add-key.yml --ask-pass
```

This should now report `changed=0`. The key is already allowed, so Ansible leaves it alone.

This behavior is called **idempotence**: repeating this instruction does not keep
adding another copy of the same key.

We still use `--ask-pass` here so you can learn that behavior without also setting
up Ubuntu to use your Windows private key. That comes next.

## You have finished this exercise when...

- You know which file lists the VM and which file describes the job.
- The job finishes with no failed or unreachable tasks.
- A new Windows SSH connection works using your key.
- Repeating the job reports no change.

Continue with [NEXT-STEPS.md](NEXT-STEPS.md) when you reach that point.
