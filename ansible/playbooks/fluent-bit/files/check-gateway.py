"""Check the host can reach the gateway, trust its certificate and use its token.

Ansible sends settings through stdin. Never print the token or request headers.
An empty OTLP request tests access without inserting a log into Loki.
"""

import http.client
import json
import socket
import ssl
import sys


def check(settings):
    context = ssl.create_default_context(cadata=settings["ca"])

    def post(token=None):
        with socket.create_connection((settings["host"], settings["port"]), timeout=10) as tcp:
            with context.wrap_socket(tcp, server_hostname=settings["tls_name"]) as connection:
                headers = [
                    "POST /v1/logs HTTP/1.1",
                    "Host: " + settings["tls_name"],
                    "User-Agent: agent-local",
                    "Content-Type: application/json",
                    "Content-Length: 2",
                    "Connection: close",
                ]
                if token is not None:
                    headers.append("Authorization: Bearer " + token)
                connection.sendall(("\r\n".join(headers) + "\r\n\r\n{}").encode())
                response = http.client.HTTPResponse(connection)
                response.begin()
                status = response.status
                response.read()
                return status

    if post() != 401:
        raise RuntimeError("Gateway did not require a bearer token; check the endpoint")
    if post(settings["token"]) != 200:
        raise RuntimeError("Gateway rejected the authenticated OTLP request")


if __name__ == "__main__":
    try:
        check(json.load(sys.stdin))
    except (OSError, ValueError, RuntimeError, http.client.HTTPException) as error:
        print("Gateway check failed: " + str(error), file=sys.stderr)
        sys.exit(1)
    print("Gateway reachable; certificate and token accepted")
