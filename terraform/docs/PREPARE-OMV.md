# Hydra: prepare an OMV source, not an Ubuntu cloud image

Observed Hydra: OpenMediaVault 8.5.11-1, 1 vCPU, 1024 MiB RAM, 16-GiB local-zfs OS
disk, static 192.168.63.113/24, gateway .1, DNS .102, root SSH account. Physical
NAS data comes from a USB device observed as Endgame port 2-10, not a second virtual disk.

This NAS stack deliberately uses a dedicated source with its fixed network already
configured through OMV. It does NOT pretend that a generic cloud-init network file
will keep OMV's internal configuration database in sync.

## Build source template 9102 on Endgame

1. Obtain the official OMV 8 installer (Debian 13 base), verify its published checksum,
   and record the exact ISO/package version. The observed version is 8.5.11-1; use
   retained matching packages if exact version parity is required. Do not silently
   claim that the latest OMV 8 installer is the same version.
2. Create a NEW VM 9102, named hydra-omv8-template, on Endgame. Use SeaBIOS,
   virtio-scsi-single, a 16-GiB scsi0 disk on local-zfs, one core, 1024 MiB RAM,
   cpu=host, and a VirtIO NIC on vmbr0. Use a temporary UNIQUE MAC and temporary
   installation network while the real Hydra is present. Attach only the installer;
   never attach the live USB data disk to the template.
3. Install OMV onto that OS disk. Set a root password through its console if required
   for initial setup; don't put it in Terraform. Install qemu-guest-agent and enable
   the VM's agent channel, then verify it works. Enable SSH/root key access using
   OMV's supported settings and authorize your laptop public key for root. Test it.
4. On the isolated replacement network, give the source VM's NIC the future Hydra
   MAC BC:24:11:05:E6:58 before its final OMV network setup. The source will remain
   stopped as a template when the clone runs, so only the clone may use that identity.
   In OMV's own network settings configure the future Hydra identity: hostname hydra,
   interface ens18, address 192.168.63.113/24, gateway 192.168.63.1, DNS .102. Do this
   only on the isolated replacement network or through its console while disconnected
   from the occupied production LAN. The template is dedicated to this SINGLE Hydra
   clone, not a generic NAS image to run twice.
5. Remove the installer media and verify OS boots from scsi0. Do not configure a data
   filesystem, shares, exports or persistent mounts pointing at the USB data disk.
6. Prepare unique host identity for the clone. In the template, install a one-time
   service BEFORE removing host keys, then shut down immediately after cleanup:

```bash
# Run INSIDE the new source VM, never inside the live Hydra.
cat > /etc/systemd/system/lab-first-boot-ssh.service <<'UNIT'
[Unit]
Description=Generate unique SSH host keys for a new NAS clone
Before=ssh.service ssh.socket
ConditionPathExists=!/etc/ssh/ssh_host_ed25519_key
[Service]
Type=oneshot
ExecStart=/usr/bin/ssh-keygen -A
[Install]
WantedBy=multi-user.target
UNIT
systemctl enable lab-first-boot-ssh.service
rm -f /etc/ssh/ssh_host_*
truncate -s 0 /etc/machine-id
# If /var/lib/dbus/machine-id is a regular file, replace it with a symlink to
# /etc/machine-id as appropriate for this installed Debian image before capture.
sync
poweroff
```

7. On Endgame confirm 9102 is stopped, has no USB attachment or data disk, its
   cloud-init drive is absent, and its root disk is exactly 16G. Convert it to a
   template with `qm template 9102`. Never boot this source again for normal use.
8. Make a temporary test clone on the isolated network WITHOUT USB passthrough.
   Verify root key login, machine-id/SSH fingerprint uniqueness, guest-agent health,
   OMV UI, static network persistence and its ability to retain OMV settings across
   a reboot. Inspect actual rendered network names/MAC matching: it must work with
   the final MAC BC:24:11:05:E6:58, not remain tied to the template's temporary MAC.
   Delete only that confirmed temporary clone after testing.

Keep the prepared template and its installer/build record. It is an input artifact,
not created by Terraform. This manual OS preparation is the explicit prerequisite
for repeatable NAS VM cloning; the project does not automate the OMV installer.

## USB mapping

Create/review the Proxmox cluster resource mapping hydra-data for the actual NAS USB
device on Endgame. Confirm vendor/product/serial and physical ownership before binding
it; 2-10 is only the observed source machine's port path. The pinned provider accepts
`usb { mapping = "hydra-data" }`; permissions for resource mappings are separate
from ordinary VM cloning. Follow the installed Proxmox API schema/official mapping
procedure instead of guessing a vendor/product ID from the name of a disk.

A replacement USB disk can be empty; preserving the old USB disk preserves its files.
Terraform does not recreate those files or the old OMV shares. Do not format an old
data disk as part of deployment. NFS/shares/data recovery are deliberately later work.

After all source checks pass, set omv_template_ready=true in a local override file or
on the NAS command line, then use the NAS deployment instructions. That flag is an
operator confirmation, not a test that the source OS is correctly prepared.

References: [OMV installation](https://docs.openmediavault.org/en/stable/installation/index.html),
[official OMV downloads](https://www.openmediavault.org/download.html).
