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

variable "template_vm_id" { type = number }
variable "template_node" { type = string }
variable "omv_template_ready" {
  type        = bool
  default     = false
  description = "Confirm a clean Hydra-specific 16-GiB OMV template has passed the preparation checklist."
}
variable "usb_mapping" {
  type        = string
  description = "Reviewed Proxmox USB resource mapping for Hydra's data disk; must point to the intended device on Endgame."
}
