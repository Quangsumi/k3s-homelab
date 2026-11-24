variable "keycloak_url" {
  description = "Base HTTPS URL your guests use to reach Keycloak."
  type        = string
  default     = "https://auth.lab"
}

variable "app_client_id" {
  description = "App name used in its client, guest realm, and viewer group."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9]*(-[a-z0-9]+)*$", var.app_client_id))
    error_message = "Use lowercase letters and numbers separated by single dashes. Start with a letter."
  }
}

variable "app_callback_url" {
  description = "Exact HTTPS return URL given by the app's OpenID Connect configuration."
  type        = string

  validation {
    condition     = can(regex("^https://[^/\\s@*#]+/[^\\s*#]*$", var.app_callback_url))
    error_message = "Enter a full HTTPS callback URL with its exact path and no wildcard or fragment."
  }
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
