terraform {
  required_version = ">= 1.9.0"

  required_providers {
    keycloak = {
      source  = "keycloak/keycloak"
      version = "5.11.0"
    }
  }
}

provider "keycloak" {
  url   = trimsuffix(var.keycloak_url, "/")
  realm = "master"
}

resource "keycloak_realm" "guest" {
  realm                    = "guests-${var.app_client_id}"
  enabled                  = true
  registration_allowed     = false
  duplicate_emails_allowed = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "keycloak_group" "viewers" {
  realm_id = keycloak_realm.guest.id
  name     = "grp-${var.app_client_id}-guest-viewers"
}

resource "keycloak_role" "invited" {
  realm_id    = keycloak_realm.guest.id
  name        = "rrl-${var.app_client_id}-guest-access"
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

resource "keycloak_openid_client" "app" {
  realm_id                     = keycloak_realm.guest.id
  client_id                    = var.app_client_id
  access_type                  = "CONFIDENTIAL"
  standard_flow_enabled        = true
  direct_access_grants_enabled = false
  service_accounts_enabled     = false
  valid_redirect_uris          = [var.app_callback_url]
  pkce_code_challenge_method   = "S256"

  depends_on = [keycloak_authentication_bindings.guest]
}

resource "keycloak_openid_group_membership_protocol_mapper" "guest_groups" {
  realm_id            = keycloak_realm.guest.id
  client_id           = keycloak_openid_client.app.id
  name                = "Guest groups"
  claim_name          = "groups"
  full_path           = false
  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}

output "issuer_url" {
  description = "Keycloak address the guest app uses to discover its sign-in endpoints."
  value       = "${trimsuffix(var.keycloak_url, "/")}/realms/${keycloak_realm.guest.realm}"
}

output "app_client_id" {
  description = "Client ID to enter in the guest app."
  value       = keycloak_openid_client.app.client_id
}

output "viewer_group" {
  description = "Name to map to the app's read-only permissions."
  value       = keycloak_group.viewers.name
}
