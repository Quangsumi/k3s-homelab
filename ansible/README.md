# Learn Ansible with your VMs

Start with one job: **add your laptop's SSH public key to Valkyrie**.
After that works, move to the other VMs and other settings.
Use your existing VM account (for example `valkyrie`), with sudo for administrator
tasks. Root can remain locked.
If you want to prepare direct root access afterward, follow [ROOT-ACCESS.md](ROOT-ACCESS.md).

## Read in this order

1. [First exercise](LESSONS.md): understand the job, read two small files, preview it, run it and check the result.
2. [Laptop setup](SETUP.md): install Ansible in Ubuntu on Windows. The exercise tells you when to open this page.
3. [Next steps](NEXT-STEPS.md): use keys from Ubuntu, manage different VM passwords, install software, and understand networking.
4. [Network changes](NETWORKING.md): the automated DNS job: preserve current networking, back up, apply, verify or roll back.

Each command in the first exercise says **where to run it**, what it does, and
what result to expect. Example output is labeled as an example.

## Which files should I open first?

```text
beginner/hosts.yml      The machine list: Valkyrie only.
beginner/add-key.yml    The job: add your laptop's public key.
keys/laptop.pub         Your public key; you supply this file.
```

The first exercise asks for one VM password. You do not need the encrypted password
file or the full lab settings to complete it.

## What is the rest of the project for?

For key-only runs, no Vault prompt is needed. Encrypted credentials now live in
`secrets/vault.yml`; [VAULT.md](VAULT.md) explains when to load them.

The `inventory/` and `playbooks/` folders contain the full lab version.
[NEXT-STEPS.md](NEXT-STEPS.md) introduces those files after the first exercise.
[REFERENCE.md](REFERENCE.md) holds the technical details and source links.
[NAMING.md](NAMING.md) explains stable VM names and moving from the earlier numbered names.
[HOST-EXCEPTIONS.md](HOST-EXCEPTIONS.md) explains Hydra's root account and Biteforce's key-only login, with retry commands.

The machine addresses came from the triage skill's October 13, 2026 notes. Confirm
them before use. Creating and rewriting these files has not contacted or changed VMs.

The network playbook now applies DNS changes automatically, with a local rollback
timer. Use --check first. It preserves current IP/IPv6/interface rules and excludes
Hydra. No network changes have been applied during preparation.

See [VALIDATION.md](VALIDATION.md) for checks performed and checks still needed.
