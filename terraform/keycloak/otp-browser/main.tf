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

resource "keycloak_authentication_flow" "otp_browser" {
  realm_id    = local.realm
  alias       = "Authenticator Code Browser"
  description = "Require the user's enrolled authenticator code during browser sign-in."
}

resource "keycloak_authentication_execution" "password" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_flow.otp_browser.alias
  authenticator     = "auth-username-password-form"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_authentication_subflow" "registered_code" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_flow.otp_browser.alias
  alias             = "Authenticator Code Browser - Registered code"
  provider_id       = "basic-flow"
  requirement       = "CONDITIONAL"
  priority          = 20
}

resource "keycloak_authentication_execution" "code_configured" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.registered_code.alias
  authenticator     = "conditional-user-configured"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_authentication_execution" "otp" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.registered_code.alias
  authenticator     = "auth-otp-form"
  requirement       = "REQUIRED"
  priority          = 20
}

resource "keycloak_authentication_subflow" "missing_code" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_flow.otp_browser.alias
  alias             = "Authenticator Code Browser - Deny if code is missing"
  provider_id       = "basic-flow"
  requirement       = "CONDITIONAL"
  priority          = 30
}

resource "keycloak_authentication_execution" "code_check_skipped" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.missing_code.alias
  authenticator     = "conditional-sub-flow-executed"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_authentication_execution_config" "code_check_skipped" {
  realm_id     = local.realm
  execution_id = keycloak_authentication_execution.code_check_skipped.id
  alias        = "Authenticator Code Browser - Check registered code branch"

  config = {
    flow_to_check = keycloak_authentication_subflow.registered_code.alias
    check_result  = "not-executed"
  }
}

resource "keycloak_authentication_execution" "deny" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.missing_code.alias
  authenticator     = "deny-access-authenticator"
  requirement       = "REQUIRED"
  priority          = 20
}
