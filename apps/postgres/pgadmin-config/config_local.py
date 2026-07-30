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
            "pgadmin_roles": ["pgadmin-access"],
        },
        "OAUTH2_SSL_CERT_VERIFICATION": True,
        "OAUTH2_CHALLENGE_METHOD": "S256",
        "OAUTH2_RESPONSE_TYPE": "code",
    }
]