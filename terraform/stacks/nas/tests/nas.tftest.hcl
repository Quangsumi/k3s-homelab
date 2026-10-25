mock_provider "proxmox" {}

run "hydra_hardware_without_data_formatting" {
  command = plan
  variables {
    fresh_target_confirmed = true
    omv_template_ready     = true
  }
  assert {
    condition     = proxmox_virtual_environment_vm.hydra.vm_id == 108 && proxmox_virtual_environment_vm.hydra.node_name == "endgame"
    error_message = "Hydra must retain its recorded ID and physical host binding."
  }
  assert {
    condition     = proxmox_virtual_environment_vm.hydra.memory[0].dedicated == 1024 && proxmox_virtual_environment_vm.hydra.disk[0].size == 16
    error_message = "Preserve Hydra's 1-GiB RAM and 16-GiB OS disk."
  }
  assert {
    condition     = proxmox_virtual_environment_vm.hydra.usb[0].mapping == "hydra-data" && length(proxmox_virtual_environment_vm.hydra.disk) == 1
    error_message = "USB data must be passed through; do not invent or format a second virtual disk."
  }
}
