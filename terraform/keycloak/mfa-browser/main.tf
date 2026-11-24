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
  levels = {
    password      = { label = "Password", number = 1, max_age = 36000, priority = 10 }
    second_factor = { label = "Second factor", number = 2, max_age = 300, priority = 20 }
  }
}

provider "keycloak" {
  url   = "https://auth.lab"
  realm = local.realm
}

resource "keycloak_authentication_flow" "mfa_browser" {
  realm_id    = local.realm
  alias       = "Password and Second Factor Browser"
  description = "Reuse a recent password and require an authenticator code or security key at level 2."
}

resource "keycloak_authentication_subflow" "identify" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_flow.mfa_browser.alias
  alias             = "${keycloak_authentication_flow.mfa_browser.alias} - Identify and verify"
  requirement       = "REQUIRED"
  priority          = 10
}

# Keycloak tries the current session first. An expired or missing level falls
# through to the sign-in steps because both are alternatives in the same branch.
resource "keycloak_authentication_execution" "cookie" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.identify.alias
  authenticator     = "auth-cookie"
  requirement       = "ALTERNATIVE"
  priority          = 10
}

resource "keycloak_authentication_subflow" "step_up" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.identify.alias
  alias             = "${keycloak_authentication_flow.mfa_browser.alias} - Sign in or step up"
  requirement       = "ALTERNATIVE"
  priority          = 20
}

resource "keycloak_authentication_subflow" "level" {
  for_each = local.levels

  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.step_up.alias
  alias             = "${keycloak_authentication_flow.mfa_browser.alias} - Level ${each.value.number} - ${each.value.label}"
  requirement       = "CONDITIONAL"
  priority          = each.value.priority
}

resource "keycloak_authentication_execution" "level_check" {
  for_each = keycloak_authentication_subflow.level

  realm_id          = local.realm
  parent_flow_alias = each.value.alias
  authenticator     = "conditional-level-of-authentication"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_authentication_execution_config" "level_check" {
  for_each = keycloak_authentication_execution.level_check

  realm_id     = local.realm
  execution_id = each.value.id
  alias        = "${keycloak_authentication_flow.mfa_browser.alias} - ${local.levels[each.key].label} reuse"
  config = {
    "loa-condition-level" = tostring(local.levels[each.key].number)
    "loa-max-age"         = tostring(local.levels[each.key].max_age)
  }
}

resource "keycloak_authentication_execution" "password" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.level["password"].alias
  authenticator     = "auth-username-password-form"
  requirement       = "REQUIRED"
  priority          = 20
}

# Level 2 succeeds after either alternative. Keeping the choice required
# prevents a user with neither method enrolled from signing in with a password alone.
resource "keycloak_authentication_subflow" "second_factor" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.level["second_factor"].alias
  alias             = "${keycloak_authentication_flow.mfa_browser.alias} - OTP or security key"
  provider_id       = "basic-flow"
  requirement       = "REQUIRED"
  priority          = 20
}

resource "keycloak_authentication_execution" "security_key" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.second_factor.alias
  authenticator     = "webauthn-authenticator"
  requirement       = "ALTERNATIVE"
  priority          = 10
}

resource "keycloak_authentication_execution" "otp" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.second_factor.alias
  authenticator     = "auth-otp-form"
  requirement       = "ALTERNATIVE"
  priority          = 20
}
