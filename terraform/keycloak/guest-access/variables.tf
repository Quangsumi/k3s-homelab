variable "keycloak_url" {
  description = "Base HTTPS URL your guests use to reach Keycloak."
  type        = string
  default     = "https://auth.lab"
}

variable "enable_guest_sign_in" {
  description = "Allow guest-realm sign-in to homelab after app access rules are ready."
  type        = bool
  default     = false
}

variable "github_client_id" {
  description = "Client ID from the GitHub OAuth app created for this guest realm."
  type        = string
}

variable "github_client_secret" {
  description = "Secret from that GitHub OAuth app. Supply it through the environment."
  type        = string
  sensitive   = true
}
