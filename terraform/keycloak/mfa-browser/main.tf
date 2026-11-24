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
  realm = "homelab"
}

provider "keycloak" {
  url   = "https://auth.lab"
  realm = local.realm
}

resource "keycloak_authentication_flow" "mfa_browser" {
  realm_id    = local.realm
  alias       = "Password and Second Factor Browser"
  description = "Require a password followed by an authenticator code or security key."
}

resource "keycloak_authentication_execution" "password" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_flow.mfa_browser.alias
  authenticator     = "auth-username-password-form"
  requirement       = "REQUIRED"
  priority          = 10
}

# This subflow must succeed. Keycloak only needs one of its alternatives.
# A user with neither method enrolled cannot satisfy the subflow.
resource "keycloak_authentication_subflow" "second_factor" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_flow.mfa_browser.alias
  alias             = "${keycloak_authentication_flow.mfa_browser.alias} - Choose second factor"
  provider_id       = "basic-flow"
  requirement       = "REQUIRED"
  priority          = 20
}

resource "keycloak_authentication_execution" "otp" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.second_factor.alias
  authenticator     = "auth-otp-form"
  requirement       = "ALTERNATIVE"
  priority          = 10
}

resource "keycloak_authentication_execution" "security_key" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.second_factor.alias
  authenticator     = "webauthn-authenticator"
  requirement       = "ALTERNATIVE"
  priority          = 20
}
