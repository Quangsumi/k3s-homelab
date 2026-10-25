output "fleet" {
  description = "Address-book data for manual verification and later Ansible work."
  value = { for name, vm in var.vms : name => {
    vm_id         = module.vm[name].vm_id
    node          = vm.node
    address       = vm.address
    hostname      = "${name}.lab"
    ssh_user      = name
    intended_role = vm.role
    os_disk_gib   = local.resolved_vms[name].disk_gib
    os_datastore  = local.resolved_vms[name].datastore
  } }
}
output "cloud_config_preview" { value = local.user_data }
output "network_config_preview" { value = local.network_data }
