variable "name" { type = string }
variable "spec" {
  type = object({
    vm_id               = number
    node                = string
    address             = string
    role                = string
    cores               = number
    memory_mib          = number
    disk_gib            = number
    datastore           = string
    cloudinit_datastore = string
    mac                 = string
    firewall            = bool
  })
}
variable "template" { type = object({ vm_id = number, disk_gib = number }) }
variable "user_data_file_id" { type = string }
variable "network_data_file_id" { type = string }
variable "fresh_target_confirmed" { type = bool }
