terraform {
  required_version = ">= 1.9.0"

  required_providers {
    keycloak = {
      source  = "keycloak/keycloak"
      version = "5.11.0"
    }
  }
}

locals {
  keycloak_url = trimsuffix(var.keycloak_url, "/")
  guest_realm  = "guest-realm"
  viewer_group = "grp-guest-viewer"

  guest_issuer = "${local.keycloak_url}/realms/${local.guest_realm}"
  guest_oidc   = "${local.guest_issuer}/protocol/openid-connect"
}

provider "keycloak" {
  url   = local.keycloak_url
  realm = "master"
}

resource "keycloak_realm" "guest" {
  realm                    = local.guest_realm
  enabled                  = true
  registration_allowed     = false
  duplicate_emails_allowed = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "keycloak_group" "viewers" {
  realm_id = keycloak_realm.guest.id
  name     = local.viewer_group
}

resource "keycloak_role" "invited" {
  realm_id    = keycloak_realm.guest.id
  name        = "rrl-guest-access"
  description = "Allows an invited account through the guest sign-in checks."
}

resource "keycloak_group_roles" "viewers" {
  realm_id = keycloak_realm.guest.id
  group_id = keycloak_group.viewers.id
  role_ids = [keycloak_role.invited.id]
}

resource "keycloak_oidc_github_identity_provider" "guest" {
  realm                         = keycloak_realm.guest.id
  alias                         = "github"
  display_name                  = "GitHub"
  client_id                     = var.github_client_id
  client_secret                 = var.github_client_secret
  default_scopes                = "user:email"
  trust_email                   = false
  store_token                   = false
  sync_mode                     = "IMPORT"
  first_broker_login_flow_alias = keycloak_authentication_flow.guest["first_login"].alias
  post_broker_login_flow_alias  = keycloak_authentication_flow.guest["post_login"].alias

  depends_on = [
    keycloak_authentication_execution.detect_existing_guest,
    keycloak_authentication_execution.prove_existing_account,
    keycloak_authentication_execution.allow,
    keycloak_authentication_execution.deny,
    keycloak_authentication_execution_config.invited_role,
    keycloak_authentication_execution_config.invitation_missing,
  ]
}

# homelab is the only application that connects to the guest realm.
resource "keycloak_openid_client" "homelab_broker" {
  realm_id                     = keycloak_realm.guest.id
  client_id                    = "homelab-guest-broker"
  access_type                  = "CONFIDENTIAL"
  standard_flow_enabled        = true
  direct_access_grants_enabled = false
  service_accounts_enabled     = false
  valid_redirect_uris          = [local.homelab_callback]
  pkce_code_challenge_method   = "S256"

  depends_on = [keycloak_authentication_bindings.guest]
}

resource "keycloak_openid_group_membership_protocol_mapper" "guest_groups" {
  realm_id            = keycloak_realm.guest.id
  client_id           = keycloak_openid_client.homelab_broker.id
  name                = "Guest groups"
  claim_name          = "groups"
  full_path           = false
  add_to_id_token     = true
  add_to_access_token = false
  add_to_userinfo     = false
}

output "github_callback_url" {
  description = "Authorization callback URL for the GitHub OAuth app."
  value       = "${local.guest_issuer}/broker/github/endpoint"
}

output "viewer_group" {
  description = "Name to map to the app's read-only permissions."
  value       = keycloak_group.homelab_viewers.name
}
