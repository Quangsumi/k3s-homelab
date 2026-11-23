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
  realm        = "homelab"
  keycloak_url = "https://auth.lab"
  levels = {
    password = { label = "Password", number = 1, max_age = 36000, priority = 10 }
    passkey  = { label = "Passkey", number = 2, max_age = 300, priority = 20 }
  }
}

provider "keycloak" {
  url   = local.keycloak_url
  realm = local.realm
}

variable "authenticator_attachment" {
  description = "One realm-wide device choice for new WebAuthn registrations."
  type        = string
  nullable    = false

  validation {
    condition     = contains(["cross-platform", "not specified"], var.authenticator_attachment)
    error_message = "Select cross-platform or not specified."
  }
}

resource "keycloak_authentication_flow" "passkey" {
  realm_id    = local.realm
  alias       = "Critical Infrastructure Browser (Terraform)"
  description = "Require an enrolled passkey and reuse the check for up to five minutes."
}

resource "keycloak_authentication_subflow" "identify" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_flow.passkey.alias
  alias             = "${keycloak_authentication_flow.passkey.alias} - Identify and verify"
  requirement       = "REQUIRED"
  priority          = 10
}

# Cookie and step-up must be alternatives inside the same required branch.
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
  alias             = "${keycloak_authentication_flow.passkey.alias} - Sign in or step up"
  requirement       = "ALTERNATIVE"
  priority          = 20
}

resource "keycloak_authentication_subflow" "level" {
  for_each = local.levels

  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.step_up.alias
  alias             = "${keycloak_authentication_flow.passkey.alias} - Level ${each.value.number} - ${each.value.label}"
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
  alias        = "${keycloak_authentication_flow.passkey.alias} - ${local.levels[each.key].label} reuse"
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

resource "keycloak_authentication_subflow" "registered" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.level["passkey"].alias
  alias             = "${keycloak_authentication_flow.passkey.alias} - Registered passkey"
  requirement       = "CONDITIONAL"
  priority          = 20
}

resource "keycloak_authentication_execution" "key_configured" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.registered.alias
  authenticator     = "conditional-user-configured"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_authentication_execution" "webauthn" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.registered.alias
  authenticator     = "webauthn-authenticator"
  requirement       = "REQUIRED"
  priority          = 20
}

resource "keycloak_authentication_subflow" "missing_key" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.level["passkey"].alias
  alias             = "${keycloak_authentication_flow.passkey.alias} - Deny if passkey is missing"
  requirement       = "CONDITIONAL"
  priority          = 30
}

resource "keycloak_authentication_execution" "key_check_skipped" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.missing_key.alias
  authenticator     = "conditional-sub-flow-executed"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_authentication_execution_config" "key_check_skipped" {
  realm_id     = local.realm
  execution_id = keycloak_authentication_execution.key_check_skipped.id
  alias        = "${keycloak_authentication_flow.passkey.alias} - Check registered passkey branch"
  config = {
    flow_to_check = keycloak_authentication_subflow.registered.alias
    check_result  = "not-executed"
  }
}

resource "keycloak_authentication_execution" "deny" {
  realm_id          = local.realm
  parent_flow_alias = keycloak_authentication_subflow.missing_key.alias
  authenticator     = "deny-access-authenticator"
  requirement       = "REQUIRED"
  priority          = 20
}

resource "terraform_data" "enrollment_device" {
  # Apply the selected realm policy after the new, unbound flow is complete.
  depends_on = [
    keycloak_authentication_execution.cookie,
    keycloak_authentication_execution.password,
    keycloak_authentication_execution.key_configured,
    keycloak_authentication_execution.webauthn,
    keycloak_authentication_execution.deny,
    keycloak_authentication_execution_config.key_check_skipped,
    keycloak_authentication_execution_config.level_check,
  ]

  triggers_replace = {
    attachment = var.authenticator_attachment
    script     = filesha256("${path.module}/set-attachment.py")
  }

  provisioner "local-exec" {
    working_dir = path.module
    interpreter = ["python3"]
    command     = "set-attachment.py"
    environment = {
      PASSKEY_KEYCLOAK_URL   = local.keycloak_url
      PASSKEY_KEYCLOAK_REALM = local.realm
      PASSKEY_ATTACHMENT     = var.authenticator_attachment
    }
  }
}
