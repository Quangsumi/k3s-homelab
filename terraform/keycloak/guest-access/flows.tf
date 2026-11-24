locals {
  guest_flows = {
    browser     = "Guest app browser"
    first_login = "Guest first GitHub sign-in"
    post_login  = "Guest returning GitHub sign-in"
  }
}

resource "keycloak_authentication_flow" "guest" {
  for_each = local.guest_flows

  realm_id = keycloak_realm.guest.id
  alias    = each.value
}

resource "keycloak_authentication_bindings" "guest" {
  realm_id     = keycloak_realm.guest.id
  browser_flow = keycloak_authentication_flow.guest["browser"].alias

  depends_on = [keycloak_authentication_execution_config.github_redirect]
}

resource "keycloak_authentication_subflow" "identify" {
  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = keycloak_authentication_flow.guest["browser"].alias
  alias             = "Guest app browser - Identify guest"
  provider_id       = "basic-flow"
  requirement       = "REQUIRED"
  priority          = 10
}

# These two alternatives share a parent so Cookie can actually run.
resource "keycloak_authentication_execution" "cookie" {
  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = keycloak_authentication_subflow.identify.alias
  authenticator     = "auth-cookie"
  requirement       = "ALTERNATIVE"
  priority          = 10
}

resource "keycloak_authentication_execution" "github_redirect" {
  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = keycloak_authentication_subflow.identify.alias
  authenticator     = "identity-provider-redirector"
  requirement       = "ALTERNATIVE"
  priority          = 20
}

resource "keycloak_authentication_execution_config" "github_redirect" {
  realm_id     = keycloak_realm.guest.id
  execution_id = keycloak_authentication_execution.github_redirect.id
  alias        = "Send guests to GitHub"
  config       = { defaultProvider = keycloak_oidc_github_identity_provider.guest.alias }
}

# Find a pre-created account and ask the guest to prove they own it before linking.
resource "keycloak_authentication_execution" "detect_existing_guest" {
  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = keycloak_authentication_flow.guest["first_login"].alias
  authenticator     = "idp-detect-existing-broker-user"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_authentication_execution" "prove_existing_account" {
  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = keycloak_authentication_flow.guest["first_login"].alias
  authenticator     = "idp-username-password-form"
  requirement       = "REQUIRED"
  priority          = 20
}

resource "keycloak_authentication_subflow" "invited" {
  for_each = keycloak_authentication_flow.guest

  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = each.value.alias
  alias             = "${each.value.alias} - Invitation confirmed"
  provider_id       = "basic-flow"
  requirement       = "CONDITIONAL"
  priority          = 30
}

resource "keycloak_authentication_execution" "invited_role" {
  for_each = keycloak_authentication_subflow.invited

  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = each.value.alias
  authenticator     = "conditional-user-role"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_authentication_execution_config" "invited_role" {
  for_each = keycloak_authentication_execution.invited_role

  realm_id     = keycloak_realm.guest.id
  execution_id = each.value.id
  alias        = "${local.guest_flows[each.key]} - Check invitation role"
  config = {
    condUserRole = keycloak_role.invited.name
    negate       = "false"
  }
}

resource "keycloak_authentication_execution" "allow" {
  for_each = keycloak_authentication_subflow.invited

  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = each.value.alias
  authenticator     = "allow-access-authenticator"
  requirement       = "REQUIRED"
  priority          = 20
}

# Deny when the preceding branch did not confirm the invitation.
resource "keycloak_authentication_subflow" "not_invited" {
  for_each = keycloak_authentication_flow.guest

  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = each.value.alias
  alias             = "${each.value.alias} - Deny if invitation is missing"
  provider_id       = "basic-flow"
  requirement       = "CONDITIONAL"
  priority          = 40
}

resource "keycloak_authentication_execution" "invitation_missing" {
  for_each = keycloak_authentication_subflow.not_invited

  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = each.value.alias
  authenticator     = "conditional-sub-flow-executed"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_authentication_execution_config" "invitation_missing" {
  for_each = keycloak_authentication_execution.invitation_missing

  realm_id     = keycloak_realm.guest.id
  execution_id = each.value.id
  alias        = "${local.guest_flows[each.key]} - Check whether invitation was confirmed"
  config = {
    flow_to_check = keycloak_authentication_subflow.invited[each.key].alias
    check_result  = "not-executed"
  }
}

resource "keycloak_authentication_execution" "deny" {
  for_each = keycloak_authentication_subflow.not_invited

  realm_id          = keycloak_realm.guest.id
  parent_flow_alias = each.value.alias
  authenticator     = "deny-access-authenticator"
  requirement       = "REQUIRED"
  priority          = 20
}
