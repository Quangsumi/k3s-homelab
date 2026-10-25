# Prepare first: one phase at a time

These are instructions to run later. No remote preparation has been executed.
The result is fresh operating systems with SSH access, not a configured Kubernetes cluster.

## 1. Know the target

You need a replacement/empty two-node Proxmox cluster named endgame and deepsix,
management addresses .10/.11, vmbr0 on the same LAN, and local-zfs plus local-ssd
storage on each host. Install Proxmox/join nodes and create/verify pools separately.
Do not recreate those pools by guessing disk device names. VM storage names alone
never prove which physical disk they use.

The existing lab already occupies this environment's IDs/IPs/MACs. Do not run this
against it as a new deployment. A parallel lab needs separate network identities
and its own state; read BOUNDARIES.md before adapting the variables.

Verify .1 gateway and .102 DNS independently of any VM we are creating. Do not
host Terraform state or its only credentials on Hydra before Hydra exists.

## 2. Prepare the WSL/Linux workstation

Install Terraform 1.13.5 (the locally tested CLI) using HashiCorp's published binary
and checksum/signature procedure. The project accepts >=1.9,<2.0; do not upgrade the
pinned Proxmox provider during the first deployment. In Ubuntu, install the image
preparation tools, not on your live Proxmox hosts:

```bash
sudo apt update
sudo apt install -y curl qemu-utils libguestfs-tools openssh-client python3
cd '/mnt/d/OneDrive/Desktop/Side Quests/PETs/k3s-homelab/terraform'
```

Image customization uses a small local VM appliance. If libguestfs cannot use KVM
inside WSL, set these for CPU emulation (slower):

```bash
export LIBGUESTFS_BACKEND=direct
export LIBGUESTFS_BACKEND_SETTINGS=force_tcg
```

If WSL cannot run the appliance, use a separate Linux image-builder machine. Do not
install a virtualization/image-builder stack into a control-plane guest to work around it.

Keep the existing private key in ~/.ssh/homelab_laptop, with permissions 600, and
load it with ssh-agent/ssh-add when it has a passphrase. Only its .pub contents enter
Terraform. No guest passwords or private keys are generated/stored by this project.

## 3. Prepare Proxmox access and snippet storage

Terraform uses the API and SSH to upload custom cloud-init snippets. Prepare an API
user/token with VM clone/configure/start, datastore allocate/audit and required node
read rights on the intended resources; use the provider's versioned permission table
as the authoritative list. Do not assume read-only PVEAuditor can provision VMs.
Prepare root SSH-key access to both hosts for snippet upload. Terraform's SSH transport
uses the agent, not your ~/.ssh/config aliases; node IPs are explicitly supplied.
The project does not create its own initial credentials.

Trust the cluster's CA on the workstation and verify the API certificate matches the
endpoint address. Keep provider TLS verification enabled; do not solve a trust failure
by setting insecure=true. Set credentials for the current terminal without committing
or pasting secrets into Terraform files:

```bash
read -r -s -p 'Proxmox token (user@realm!id=secret): ' PROXMOX_VE_API_TOKEN
printf '\n'
export PROXMOX_VE_API_TOKEN
```

To attach Hydra's USB device using a restricted API user, first create a reviewed
cluster USB resource mapping called hydra-data with permission for that user. It
must map to the intended Endgame USB disk currently at 2-10. Use the installed
Proxmox mapping UI/API, after inspecting the device's vendor/product/serial. Inspect
its schema before scripting: `pvesh usage /cluster/mapping/usb -v`. Do not rely on
port numbering being identical on a new physical server. No disk format/mount command
is part of Terraform. The live USB disk must not be attached to two running guests.

On the fresh cluster, enable snippets for the local directory storage. This preserves
its currently recorded content types and adds snippets:

```bash
# Run as root on ONE Proxmox cluster node; storage config is cluster-wide.
# First check pvesm config: preserve any additional content types on your target.
pvesm config
pvesm set local --content vztmpl,import,iso,rootdir,images,backup,snippets
```

The currently recorded local content lacks snippets, so Terraform uploads otherwise
fail. This preparation changes storage metadata, not disk pools.

## 4. Build the lightweight Ubuntu image once

From the terraform folder on your Linux image-builder:

```bash
bash scripts/build-ubuntu-image.sh
```

The script downloads Ubuntu Server Minimal 24.04 amd64 build 20261017, verifies its
recorded SHA256, and prepares an offline copy with cloud-init, Python 3, OpenSSH,
sudo and qemu-guest-agent. It clears instance/machine-ID cache and baked SSH host keys.
New keys and guest identity are generated at clone initialization. It does not
contact the lab or install Ansible/K3s into the image.

The base image is pinned. Package installation still uses current Ubuntu repositories,
so repeated image builds are not byte-for-byte reproducible. Reuse the SAME prepared
artifact on both hosts and retain its SHA256 for later rebuilds. For stricter package
reproducibility, retain that artifact/package repository snapshot rather than silently
rebuilding it from newer repositories.

Result: artifacts/ubuntu-24.04-minimal-lab-v1.qcow2 and its .sha256 file. Build failure
can leave a partial output; inspect it and intentionally remove/version only that local
build artifact before retrying. The script refuses to overwrite an existing output.

## 5. Make the Ubuntu templates

Copy the SAME prepared image and scripts/create-ubuntu-template.sh to each fresh
Proxmox host (e.g. /var/lib/vz/template/import/). Keep image caches out of /root.
Get its hash with `sha256sum artifacts/ubuntu-24.04-minimal-lab-v1.qcow2` locally.
Then run on the corresponding host, replacing the final hash argument:

```bash
# Endgame, root shell:
bash /path/create-ubuntu-template.sh endgame 9100 /absolute/path/ubuntu-24.04-minimal-lab-v1.qcow2 PREPARED_IMAGE_SHA256
# Deep Six, root shell:
bash /path/create-ubuntu-template.sh deepsix 9101 /absolute/path/ubuntu-24.04-minimal-lab-v1.qcow2 PREPARED_IMAGE_SHA256
```

The script checks host identity, unused cluster-wide ID and image hash, creates a
local-zfs template with an 8-GiB scsi0 disk, a cloud-init drive and guest-agent channel.
It does not boot that template. Its source must remain installed for future clones.
Do not rerun it against a partial template: inspect the partial result first; no
automatic deletion/cleanup of Proxmox resources is implemented.

## 6. Test a disposable Ubuntu clone before trusting the template

On each fresh target node, choose an unused temporary ID (e.g. 9200 or 9201) and
clone its corresponding source. In Proxmox set cloud-init username/key, use a known
unused temporary IP or DHCP, boot, and connect with the key. This is a preparation
boot test, not a command to clone onto the occupied production network.

Inside that temporary VM verify:

```bash
sudo cloud-init status --wait
ip -brief address
python3 --version
sudo -n true
systemctl is-active qemu-guest-agent
```

Also verify QEMU guest-agent communication from Proxmox, a new SSH key login and
its host fingerprint. Check SeaBIOS actually boots the prepared image. If it doesn't,
fix the source before deploying; do not silently change firmware on an existing guest.
Check that two test clones have DIFFERENT /etc/machine-id and SSH host-key fingerprints.
Use the project's network-data in the eventual fleet to enforce ens18 by MAC match.

Stop/remove only your confirmed disposable test guests after validation, not source
templates and never existing fleet IDs. Template IDs stay 9100/9101.

## 7. Prepare the dedicated OpenMediaVault source

Follow [PREPARE-OMV.md](PREPARE-OMV.md). Hydra is not an Ubuntu guest. Do not make its
source by cloning the live NAS, copying NAS files, or baking credentials/data disks
into an image. Only proceed when its dedicated template and USB mapping are verified.

## 8. Preflight and deployment

On a fresh Proxmox node, run the read-only checker:

```bash
python3 /path/preflight.py
```

It must pass unused VM IDs, template capacities and storage availability. It does
not prove unused LAN IPs or physical disk health. Verify those separately, then follow
[DEPLOY.md](DEPLOY.md). On your live cluster this check SHOULD fail on occupied IDs.

## Official references

* [Ubuntu Minimal image directory](https://cloud-images.ubuntu.com/minimal/releases/noble/)
* [Cloud-init image cleaning](https://docs.cloud-init.io/en/latest/reference/cli.html)
* [Provider cloud-init guide](https://bpg.sh/docs/guides/cloud-init/)
* [Pinned provider access requirements](https://github.com/bpg/terraform-provider-proxmox/blob/v0.117.0/docs/index.md)
