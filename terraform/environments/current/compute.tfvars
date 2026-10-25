# Fresh isolated rebuild ONLY. These IDs, MACs and IPs already exist on the live lab.
proxmox_endpoint  = "https://192.168.63.10:8006/"
node_addresses    = { endgame = "192.168.63.10", deepsix = "192.168.63.11" }
gateway           = "192.168.63.1"
prefix_length     = 24
dns_servers       = ["192.168.63.102"]
snippet_datastore = "local"
templates = {
  endgame = { vm_id = 9100, disk_gib = 8 }
  deepsix = { vm_id = 9101, disk_gib = 8 }
}
vms = {
  tombstone = { vm_id = 100, node = "endgame", address = "192.168.63.20", role = "control-plane", cores = 2, memory_mib = 2560, mac = "BC:24:11:BD:1F:6A", firewall = false }
  whyachi   = { vm_id = 101, node = "endgame", address = "192.168.63.21", role = "control-plane", cores = 2, memory_mib = 2048, mac = "BC:24:11:B1:B8:F4", firewall = false }
  biteforce = { vm_id = 111, node = "deepsix", address = "192.168.63.67", role = "control-plane", cores = 2, memory_mib = 2560, mac = "BC:24:11:B1:24:5E", firewall = true }
  huge      = { vm_id = 104, node = "deepsix", address = "192.168.63.23", role = "worker", cores = 3, memory_mib = 4712, mac = "BC:24:11:7A:DF:A6", firewall = true }
  minotaur  = { vm_id = 106, node = "endgame", address = "192.168.63.25", role = "worker", cores = 3, memory_mib = 4712, mac = "BC:24:11:47:55:7A", firewall = true }
  valkyrie  = { vm_id = 109, node = "deepsix", address = "192.168.63.22", role = "general", cores = 2, memory_mib = 2048, mac = "BC:24:11:72:7C:A8", firewall = false }
}

# New uniform policy approved for the fresh rebuild, not captured current disk state.
disk_profiles = {
  control-plane = { disk_gib = 32, datastore = "local-zfs" }
  worker        = { disk_gib = 32, datastore = "local-ssd" }
  general       = { disk_gib = 64, datastore = "local-ssd" }
}
