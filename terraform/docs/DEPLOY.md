# Deploy after preparation

Run commands in Ubuntu/WSL, from the repository's terraform directory.
This is for a fresh replacement target, not an import/update of the running fleet.
First complete PREPARE.md, both source boot tests, capacity checks and preflight.

## 1. Load access for this terminal

```bash
cd '/mnt/d/OneDrive/Desktop/Side Quests/PETs/k3s-homelab/terraform'
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/homelab_laptop
read -r -s -p 'Proxmox token (user@realm!id=secret): ' PROXMOX_VE_API_TOKEN
printf '\n'
export PROXMOX_VE_API_TOKEN
export TF_VAR_ssh_public_key="$(cat ../ansible/keys/laptop.pub)"
```

The final line reads a PUBLIC key only. Alternatively use your original ~/.ssh/*.pub
file. Verify it matches the loaded private key. No Ansible program or playbook is run.
Validate the server fingerprints and TLS CA as described in preparation.

## 2. Initialize and validate the compute stack

```bash
terraform -chdir=stacks/compute init
terraform -chdir=stacks/compute validate
```

`init` downloads the exact locked provider and finds the local VM module.
`validate` checks syntax/schema; it does not contact the API to prove your target works.

## 3. Review a real plan on the EMPTY target

```bash
terraform -chdir=stacks/compute plan \
  -var-file=../../environments/current/compute.tfvars \
  -var=fresh_target_confirmed=true \
  -out=compute.tfplan
```

The file path is relative to stacks/compute because -chdir changes the working
folder. `fresh_target_confirmed=true` is your explicit acknowledgement that the
recorded IDs/MACs/IPs can be created here; it does not inspect the network for you.

Expect six VM creations and twelve cloud-init snippet uploads. Inspect every name,
ID, node, disk profile, MAC, cloud-init path and your PUBLIC key. The plan may read
Proxmox but must not propose deleting/moving the existing fleet. If it reports an
occupied ID, stop and correct your target; never destroy a live VM to satisfy it.
The plan file is inside stacks/compute, is ignored by Git and may contain sensitive
provider-managed data. Keep it protected, along with the state.

## 4. Apply that reviewed plan

```bash
terraform -chdir=stacks/compute apply compute.tfplan
terraform -chdir=stacks/compute output fleet
```

This creates and starts the ordinary guests. It does not install K3s or join a
cluster. Provider success/guest-agent IP visibility alone does not prove cloud-init
or SSH initialization finished. The next step is part of acceptance, not optional.

## 5. Verify each guest is ready for later configuration

Use the output's IP and VM-named login account. For example:

```bash
ssh -i ~/.ssh/homelab_laptop tombstone@192.168.63.20
sudo cloud-init status --wait
hostname
ip -brief address
resolvectl status
python3 --version
sudo -n true
systemctl is-active qemu-guest-agent
exit
```

Confirm the SSH fingerprint through the guest console before trusting a recreated
machine at an old address. Do not globally disable host-key checking to hide it.
Expected: correct hostname, ens18 with the assigned address, .102 DNS, Python 3,
passwordless sudo, guest agent active and no cloud-init error. Test .1/.102 reachability
and DNS resolution from the laptop. Add/restore DNS records using your DNS system;
cloud-init configuring a resolver does not create .lab records.

Repeat for all six VMs and check that their machine IDs and SSH host fingerprints
are distinct. Small root filesystems should have expanded to their 32/64-GiB disk
capacity. If not, inspect cloud-init growpart/resize logs rather than partitioning
an occupied production disk from a copied command.

Save a machine-readable address book for future Ansible work:

```bash
terraform -chdir=stacks/compute output -json fleet > /tmp/homelab-fleet.json
```

No Ansible inventory or existing Ansible files are changed automatically.

## 6. Deploy Hydra separately

First finish PREPARE-OMV.md. The dedicated template must have root key access,
unique identity, static OMV-managed .113 networking and no USB data embedded.
The named hydra-data mapping must identify a device used by no other running guest.

```bash
terraform -chdir=stacks/nas init
terraform -chdir=stacks/nas validate
terraform -chdir=stacks/nas plan \
  -var-file=../../environments/current/nas.tfvars \
  -var=fresh_target_confirmed=true \
  -var=omv_template_ready=true \
  -out=nas.tfplan
```

Expect ONE new VM with a 16-GiB OS clone and the reviewed USB mapping. No disk
formatting or NAS filesystem/share configuration is included. Apply only after review:

```bash
terraform -chdir=stacks/nas apply nas.tfplan
ssh -i ~/.ssh/homelab_laptop root@192.168.63.113
```

Verify root SSH, OMV UI, qemu guest agent, static network persistence and intended
USB device visibility. Do not initialize/format an existing data device in OMV.
A fresh OS clone does not contain previous NAS exports, users, mounts or files.

## 7. Later Terraform runs

Re-run plan with the same environment inputs and the same state, reviewing every
update. Keep both confirmation variables supplied for their respective stacks.
No VM should be recreated just because you re-run the files. Any replacement,
firmware/disk-policy change or node migration must be understood first.
The project enables prevent_destroy and Proxmox protection; those are guardrails,
not backups. Some changes may fail until you plan an explicit maintenance procedure.

## State and a second environment

This first version uses local state separately in stacks/compute and stacks/nas.
Back up both state files securely after deployment. Do not commit them to Git, lose
them, share one state between clusters, or use two concurrent writers.

For a second lab, use a separate working checkout/directory with NEW empty state
and copied environment inputs adapted to that target (credentials, endpoints, node
names, bridges/storage, network identities and template IDs). Do not merely change
proxmox_endpoint in the working state that owns the first fleet.
Before shared/team automation, configure a suitable independent remote backend with
locking and a unique key per cluster/stack. It must exist independently of this fleet.
