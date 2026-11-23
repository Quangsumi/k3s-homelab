"""Apply the selected enrollment device without importing the existing realm."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ATTACHMENT = "webAuthnPolicyAuthenticatorAttachment"
PROFILES = {"cross-platform", "not specified"}


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(opener, url, method, body=None, headers=None):
    request = Request(url, data=body, headers=headers or {}, method=method)
    with opener.open(request, timeout=15) as response:
        content = response.read()
    return json.loads(content) if content else None


def enrollment_update(current, attachment):
    # Keycloak replaces the whole WebAuthn policy when the relying party name
    # is present. Carry the current regular policy fields into the update.
    fields = {
        name: value
        for name, value in current.items()
        if name.startswith("webAuthnPolicy")
        and not name.startswith("webAuthnPolicyPasswordless")
    }
    if not fields.get("webAuthnPolicyRpEntityName"):
        raise ValueError("Keycloak did not return the current WebAuthn policy.")

    # The realm update also reads CIBA and PAR settings from attributes.
    # Sending only some attributes can remove the omitted ones.
    attributes = current.get("attributes")
    if not isinstance(attributes, dict) or any(
        isinstance(value, str) and len(value) >= 8 and set(value) == {"*"}
        for value in attributes.values()
    ):
        raise ValueError("Keycloak did not return an unmasked realm attributes map.")
    return {**fields, ATTACHMENT: attachment, "attributes": attributes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show", action="store_true", help="Read the current setting.")
    arguments = parser.parse_args()
    url = os.environ.get("PASSKEY_KEYCLOAK_URL", "https://auth.lab").rstrip("/")
    realm = quote(os.environ.get("PASSKEY_KEYCLOAK_REALM", "homelab"), safe="")
    attachment = os.environ.get("PASSKEY_ATTACHMENT")
    address = urlsplit(url)
    if (address.scheme != "https" or not address.hostname or address.username is not None
            or address.query or address.fragment):
        raise ValueError("Use a Keycloak HTTPS base URL without credentials, a query, or a fragment.")
    if not arguments.show and attachment not in PROFILES:
        raise ValueError("Set PASSKEY_ATTACHMENT through a Terraform profile.")

    opener = build_opener(NoRedirects())
    token = os.environ.get("KEYCLOAK_ACCESS_TOKEN")
    if not token:
        client_id = os.environ.get("KEYCLOAK_CLIENT_ID")
        client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError("Set KEYCLOAK_CLIENT_ID and KEYCLOAK_CLIENT_SECRET first.")
        form = urlencode({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }).encode()
        token_result = request_json(
            opener, f"{url}/realms/{realm}/protocol/openid-connect/token", "POST",
            body=form, headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token = token_result["access_token"]

    endpoint = f"{url}/admin/realms/{realm}"
    headers = {"Authorization": f"Bearer {token}"}
    current = request_json(opener, endpoint, "GET", headers=headers)
    if not isinstance(current, dict) or ATTACHMENT not in current:
        raise ValueError("Keycloak did not return the enrollment device setting.")
    if arguments.show or current[ATTACHMENT] == attachment:
        print(f"WebAuthn enrollment device is {current[ATTACHMENT]}.")
        return

    update = enrollment_update(current, attachment)
    request_json(
        opener, endpoint, "PUT", body=json.dumps(update).encode(),
        headers={**headers, "Content-Type": "application/json"},
    )
    result = request_json(opener, endpoint, "GET", headers=headers)
    if not isinstance(result, dict) or result.get(ATTACHMENT) != attachment:
        raise ValueError("Keycloak did not save the selected enrollment device.")
    print(f"WebAuthn enrollment device is {attachment}.")


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        sys.exit(f"Keycloak rejected the WebAuthn policy request with HTTP {error.code}.")
    except (URLError, TimeoutError):
        sys.exit("Could not reach Keycloak over HTTPS. Check the address and certificate trust.")
    except (ValueError, KeyError) as error:
        sys.exit(str(error))
