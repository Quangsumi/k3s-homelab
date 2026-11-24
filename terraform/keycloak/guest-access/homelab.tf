data "keycloak_realm" "homelab" {
  realm = "homelab"
}

locals {
  homelab_callback = "${local.keycloak_url}/realms/${data.keycloak_realm.homelab.realm}/broker/${local.guest_realm}/endpoint"
}

resource "keycloak_group" "homelab_viewers" {
  realm_id = data.keycloak_realm.homelab.id
  name     = local.viewer_group
}

resource "keycloak_authentication_flow" "homelab_first_guest_login" {
  realm_id    = data.keycloak_realm.homelab.id
  alias       = "Shared guest first sign-in"
  description = "Create a linked guest account only when its username and email are unused."
}

# A guest whose username or email matches an existing homelab user is denied.
resource "keycloak_authentication_execution" "create_unique_guest" {
  realm_id          = data.keycloak_realm.homelab.id
  parent_flow_alias = keycloak_authentication_flow.homelab_first_guest_login.alias
  authenticator     = "idp-create-user-if-unique"
  requirement       = "REQUIRED"
  priority          = 10
}

resource "keycloak_oidc_identity_provider" "guest_realm" {
  realm = data.keycloak_realm.homelab.id
  alias = local.guest_realm

  display_name                  = "Guest sign-in"
  enabled                       = var.enable_guest_sign_in
  client_id                     = keycloak_openid_client.homelab_broker.client_id
  client_secret                 = keycloak_openid_client.homelab_broker.client_secret
  issuer                        = local.guest_issuer
  authorization_url             = "${local.guest_oidc}/auth"
  token_url                     = "${local.guest_oidc}/token"
  user_info_url                 = "${local.guest_oidc}/userinfo"
  jwks_url                      = "${local.guest_oidc}/certs"
  validate_signature            = true
  trust_email                   = false
  store_token                   = false
  first_broker_login_flow_alias = keycloak_authentication_flow.homelab_first_guest_login.alias

  extra_config = {
    clientAuthMethod = "client_secret_post"
    pkceEnabled      = "true"
    pkceMethod       = "S256"
  }

  depends_on = [
    keycloak_authentication_execution.create_unique_guest,
    keycloak_openid_group_membership_protocol_mapper.guest_groups,
  ]
}

resource "keycloak_custom_identity_provider_mapper" "guest_viewer_group" {
  realm                    = data.keycloak_realm.homelab.id
  name                     = "Shared guest viewer group"
  identity_provider_alias  = keycloak_oidc_identity_provider.guest_realm.alias
  identity_provider_mapper = "oidc-advanced-group-idp-mapper"

  extra_config = {
    syncMode = "FORCE"
    claims   = jsonencode([{ key = "groups", value = keycloak_group.viewers.name }])
    group    = "/${keycloak_group.homelab_viewers.name}"
  }
}
