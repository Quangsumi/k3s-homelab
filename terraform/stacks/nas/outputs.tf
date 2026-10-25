output "hydra" {
  value = { vm_id = proxmox_virtual_environment_vm.hydra.vm_id, address = "192.168.63.113", ssh_user = "root", node = "endgame" }
}
