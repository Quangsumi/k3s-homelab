resource "proxmox_virtual_environment_vm" "this" {
  name                = var.name
  vm_id               = var.spec.vm_id
  node_name           = var.spec.node
  description         = "Fresh rebuild managed by Terraform; role=${var.spec.role}. No K3s/data restored."
  tags                = sort(["terraform", var.spec.role])
  on_boot             = true
  started             = true
  protection          = true
  reboot_after_update = false
  bios                = "seabios"
  scsi_hardware       = "virtio-scsi-single"
  boot_order          = ["scsi0"]

  clone {
    vm_id        = var.template.vm_id
    node_name    = var.spec.node
    datastore_id = var.spec.datastore
    full         = true
    retries      = 3
  }
  cpu {
    cores   = var.spec.cores
    sockets = 1
    type    = "host"
    numa    = false
  }
  memory { dedicated = var.spec.memory_mib }
  agent {
    enabled = true
    timeout = "10m"
  }
  # A small, uniform source image is expanded using the role's disk profile.
  disk {
    interface    = "scsi0"
    datastore_id = var.spec.datastore
    size         = var.spec.disk_gib
    file_format  = "raw"
    discard      = "on"
    iothread     = true
    aio          = "io_uring"
    cache        = "none"
    ssd          = false
    backup       = true
    replicate    = true
  }
  network_device {
    bridge      = "vmbr0"
    model       = "virtio"
    mac_address = var.spec.mac
    firewall    = var.spec.firewall
  }
  initialization {
    interface            = "ide2"
    datastore_id         = var.spec.cloudinit_datastore
    user_data_file_id    = var.user_data_file_id
    network_data_file_id = var.network_data_file_id
  }
  serial_device {}
  operating_system { type = "l26" }
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.fresh_target_confirmed
      error_message = "Use this only on an empty, isolated target after running preflight. Existing IDs/IPs are occupied on your live cluster."
    }
    precondition {
      condition     = var.template.disk_gib == 8 && var.spec.disk_gib >= 8 && floor(var.spec.disk_gib) == var.spec.disk_gib
      error_message = "Prepare an 8-GiB source template and a whole-GiB role disk size at least as large."
    }
    precondition {
      condition     = var.spec.vm_id != var.template.vm_id
      error_message = "A VM cannot reuse its template ID."
    }
  }
}
