variable "proxmox_endpoint" {
  type = string
}
variable "node_addresses" {
  type = map(string)
}
variable "fresh_target_confirmed" {
  description = "True only after preflight confirms this is an empty, isolated deployment target."
  type        = bool
  default     = false
}

variable "ssh_public_key" {
  description = "Existing laptop PUBLIC key. Never supply a private key or guest password."
  type        = string
  validation {
    condition     = can(regex("^ssh-(ed25519|rsa) ", trimspace(var.ssh_public_key)))
    error_message = "Supply an OpenSSH public key."
  }
}
variable "dns_servers" { type = list(string) }
variable "gateway" { type = string }
variable "prefix_length" { type = number }
variable "snippet_datastore" { type = string }
variable "templates" {
  type = map(object({ vm_id = number, disk_gib = number }))
}
variable "vms" {
  type = map(object({
    vm_id      = number
    node       = string
    address    = string
    role       = string
    cores      = number
    memory_mib = number
    mac        = string
    firewall   = bool
  }))
  validation {
    condition     = length(distinct([for v in values(var.vms) : v.vm_id])) == length(var.vms)
    error_message = "VM IDs must be unique."
  }
  validation {
    condition     = length(distinct([for v in values(var.vms) : v.address])) == length(var.vms)
    error_message = "VM IP addresses must be unique."
  }
  validation {
    condition     = alltrue([for v in values(var.vms) : v.cores >= 1 && v.memory_mib >= 512])
    error_message = "Invalid CPU or memory size."
  }
}

variable "disk_profiles" {
  description = "Shared fresh-build OS disk policy by intended role. Not a live disk migration."
  type        = map(object({ disk_gib = number, datastore = string }))
  validation {
    condition     = alltrue([for p in values(var.disk_profiles) : p.disk_gib >= 8 && floor(p.disk_gib) == p.disk_gib])
    error_message = "OS disk sizes must be whole GiB and at least 8 GiB."
  }
}
