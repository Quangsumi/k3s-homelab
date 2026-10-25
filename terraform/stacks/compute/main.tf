locals {
  resolved_vms = { for name, vm in var.vms : name => merge(vm, {
    disk_gib            = var.disk_profiles[vm.role].disk_gib
    datastore           = var.disk_profiles[vm.role].datastore
    cloudinit_datastore = var.disk_profiles[vm.role].datastore
  }) }

  user_data = { for name, vm in var.vms : name => "#cloud-config\n${yamlencode({
    hostname          = name
    fqdn              = "${name}.lab"
    manage_etc_hosts  = true
    preserve_hostname = false
    disable_root      = true
    ssh_pwauth        = false
    ssh_deletekeys    = true
    users = [{
      name                = name
      shell               = "/bin/bash"
      lock_passwd         = true
      groups              = ["sudo"]
      sudo                = ["ALL=(ALL) NOPASSWD:ALL"]
      ssh_authorized_keys = [trimspace(var.ssh_public_key)]
    }]
    growpart      = { mode = "auto", devices = ["/"], ignore_growroot_disabled = false }
    resize_rootfs = true
  })}" }
  network_data = { for name, vm in var.vms : name => yamlencode({
    version = 2
    ethernets = {
      ens18 = {
        match       = { macaddress = lower(vm.mac) }
        "set-name"  = "ens18"
        dhcp4       = false
        addresses   = ["${vm.address}/${var.prefix_length}"]
        routes      = [{ to = "default", via = var.gateway }]
        nameservers = { addresses = var.dns_servers, search = ["lab"] }
      }
    }
  }) }
}
resource "proxmox_virtual_environment_file" "user_data" {
  for_each     = var.vms
  content_type = "snippets"
  datastore_id = var.snippet_datastore
  node_name    = each.value.node
  source_raw {
    data      = local.user_data[each.key]
    file_name = "tf-${each.key}-user.yaml"
  }
}
resource "proxmox_virtual_environment_file" "network_data" {
  for_each     = var.vms
  content_type = "snippets"
  datastore_id = var.snippet_datastore
  node_name    = each.value.node
  source_raw {
    data      = local.network_data[each.key]
    file_name = "tf-${each.key}-network.yaml"
  }
}
module "vm" {
  source                 = "../../modules/linux-vm"
  for_each               = local.resolved_vms
  name                   = each.key
  spec                   = each.value
  template               = var.templates[each.value.node]
  user_data_file_id      = proxmox_virtual_environment_file.user_data[each.key].id
  network_data_file_id   = proxmox_virtual_environment_file.network_data[each.key].id
  fresh_target_confirmed = var.fresh_target_confirmed
}
