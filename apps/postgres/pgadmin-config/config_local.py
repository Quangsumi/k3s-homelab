from pathlib import Path

_client_secret = Path(
    "/etc/pgadmin/oidc/client-secret"
).read_text(encoding="utf-8").strip()

AUTHENTICATION_SOURCES = ["oauth2", "internal"]
OAUTH2_AUTO_CREATE_USER = True
MASTER_PASSWORD = True

# Traefik is the single trusted reverse proxy for this Ingress.
PROXY_X_FOR_COUNT = 1
PROXY_X_PROTO_COUNT = 1
PROXY_X_HOST_COUNT = 1
PROXY_X_PORT_COUNT = 1

# The pgAdmin session cookie expires 1 day after issue (SESSION_EXPIRATION_TIME
# in server mode). USER_INACTIVITY_TIMEOUT defaults to 0, so the separate idle
# logout is disabled. Keycloak Realm settings → Sessions and the pgadmin
# client’s Advanced overrides govern the next Keycloak sign-in.
OAUTH2_CONFIG = [
    {
        "OAUTH2_NAME": "keycloak",
        "OAUTH2_DISPLAY_NAME": "Keycloak",
        "OAUTH2_CLIENT_ID": "pgadmin",
        "OAUTH2_CLIENT_SECRET": _client_secret,
        "OAUTH2_SERVER_METADATA_URL":
            "https://auth.lab/realms/homelab/.well-known/openid-configuration",
        "OAUTH2_SCOPE": "openid email profile",
        "OAUTH2_USERNAME_CLAIM": "preferred_username",
        "OAUTH2_ADDITIONAL_CLAIMS": {
            "pgadmin_roles": ["cr-pgadmin-access"],
        },
        "OAUTH2_SSL_CERT_VERIFICATION": True,
        "OAUTH2_CHALLENGE_METHOD": "S256",
        "OAUTH2_RESPONSE_TYPE": "code",
        "OAUTH2_LOGOUT_URL": (
            "https://auth.lab/realms/homelab/protocol/openid-connect/logout"
            "?post_logout_redirect_uri={redirect_uri}"
            "&id_token_hint={id_token}"
        ),
    }
]