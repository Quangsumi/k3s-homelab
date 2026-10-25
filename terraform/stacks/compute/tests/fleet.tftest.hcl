# Mocked provider: these plans never contact Proxmox or create a VM.
mock_provider "proxmox" {}

run "recorded_fleet_and_cloud_init" {
  command = plan
  variables {
    ssh_public_key         = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestFixtureOnlyDoNotUse terraform-test"
    fresh_target_confirmed = true
  }
  assert {
    condition     = length(output.fleet) == 6
    error_message = "Expected exactly the six ordinary VMs. Hydra belongs to its own stack."
  }
  assert {
    condition     = output.fleet.biteforce.vm_id == 111 && output.fleet.valkyrie.vm_id == 109 && output.fleet.biteforce.node == "deepsix"
    error_message = "Recorded IDs/placement were changed."
  }
  assert {
    condition     = var.vms.huge.memory_mib == 4712 && var.vms.minotaur.memory_mib == 4712 && var.vms.tombstone.memory_mib == 2560
    error_message = "Preserve the measured RAM values rather than generic profiles."
  }
  assert {
    condition     = output.fleet.biteforce.os_disk_gib == 32 && output.fleet.tombstone.os_disk_gib == 32 && var.templates.deepsix.disk_gib == 8
    error_message = "Use the approved uniform 32-GiB control-plane disk policy."
  }
  assert {
    condition     = yamldecode(output.cloud_config_preview.biteforce).users[0].name == "biteforce" && yamldecode(output.cloud_config_preview.biteforce).ssh_pwauth == false
    error_message = "Cloud-init must create the named key-only account."
  }
  assert {
    condition     = yamldecode(output.network_config_preview.minotaur).ethernets.ens18.addresses[0] == "192.168.63.25/24" && yamldecode(output.network_config_preview.minotaur).ethernets.ens18.set-name == "ens18"
    error_message = "Preserve the recorded IP and MAC-matched ens18 interface name."
  }
}

run "role_storage_separation" {
  command = plan
  variables {
    ssh_public_key         = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestFixtureOnlyDoNotUse terraform-test"
    fresh_target_confirmed = true
  }
  assert {
    condition     = output.fleet.huge.os_datastore == "local-ssd" && output.fleet.minotaur.os_datastore == "local-ssd" && output.fleet.whyachi.os_datastore == "local-zfs" && output.fleet.biteforce.os_disk_gib == output.fleet.whyachi.os_disk_gib
    error_message = "Control planes and workers must use their shared role storage policy."
  }
}
