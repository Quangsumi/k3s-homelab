# API credentials come from the environment, not a tfvars file.
# PROXMOX_VE_API_TOKEN='user@realm!token=secret'
provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
  ssh {
    username = "root"
    agent    = true
    dynamic "node" {
      for_each = var.node_addresses
      content {
        name    = node.key
        address = node.value
      }
    }
  }
}
