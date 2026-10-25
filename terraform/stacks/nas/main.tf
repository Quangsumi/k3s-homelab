# Hydra uses an OMV-specific prepared template, not Ubuntu/cloud-init network writes.
resource "proxmox_virtual_environment_vm" "hydra" {
  name                = "hydra"
  vm_id               = 108
  node_name           = "endgame"
  description         = "Hydra OMV OS clone. USB data is passed through, never formatted by this project."
  tags                = ["nas", "terraform"]
  started             = true
  on_boot             = true
  protection          = true
  reboot_after_update = false
  bios                = "seabios"
  scsi_hardware       = "virtio-scsi-single"
  boot_order          = ["scsi0"]
  clone {
    vm_id        = var.template_vm_id
    node_name    = var.template_node
    datastore_id = "local-zfs"
    full         = true
    retries      = 3
  }
  cpu {
    cores   = 1
    sockets = 1
    type    = "host"
    numa    = false
  }
  memory {
    dedicated = 1024
    floating  = 0
  }
  agent { enabled = true }
  disk {
    interface    = "scsi0"
    datastore_id = "local-zfs"
    size         = 16
    file_format  = "raw"
    discard      = "on"
    iothread     = true
    aio          = "io_uring"
    cache        = "none"
    backup       = true
    replicate    = true
  }
  network_device {
    bridge      = "vmbr0"
    model       = "virtio"
    mac_address = "BC:24:11:05:E6:58"
    firewall    = true
  }
  usb { mapping = var.usb_mapping }
  startup { down_delay = 120 }
  operating_system { type = "l26" }
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.fresh_target_confirmed && var.omv_template_ready
      error_message = "Prepare and verify the clean OMV template and empty isolated target first. Never clone the live NAS or attach a USB disk that is already in use."
    }
    precondition {
      condition     = var.template_vm_id != 108 && var.template_node == "endgame"
      error_message = "Prepare the NAS template on Endgame with an unused ID, not the live Hydra ID."
    }
  }
}
