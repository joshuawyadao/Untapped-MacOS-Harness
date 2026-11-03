"""Check the test account's HTTPS transport using fixed data and safe output."""

import argparse
import http.client
import json
import os
import socket
import ssl
import sys
import tempfile
from urllib.error import URLError
from urllib.parse import urlencode

from . import game_launch, gateway


def exception_fields(error):
    """Classify an exception without copying its message, URL or response."""
    cause = error
    for _ in range(3):
        if isinstance(cause, URLError):
            cause = cause.reason
        else:
            break
    if isinstance(cause, ssl.SSLCertVerificationError):
        category = "TLS_CERTIFICATE_ERROR"
    elif isinstance(cause, ssl.SSLError):
        category = "TLS_PROTOCOL_ERROR"
    elif isinstance(cause, socket.gaierror):
        category = "DNS_ERROR"
    elif isinstance(cause, TimeoutError):
        category = "TIMEOUT"
    elif isinstance(cause, http.client.IncompleteRead):
        category = "INCOMPLETE_RESPONSE"
    elif isinstance(cause, ConnectionRefusedError):
        category = "CONNECTION_REFUSED"
    elif isinstance(cause, (ConnectionError, http.client.RemoteDisconnected)):
        category = "CONNECTION_CLOSED"
    elif isinstance(cause, OSError):
        category = "OS_ERROR"
    elif isinstance(cause, AttributeError):
        category = "RESPONSE_INTERFACE_ERROR"
    elif isinstance(cause, (TypeError, ValueError)):
        category = "INTERNAL_SHAPE_ERROR"
    else:
        category = "UNKNOWN_TRANSPORT_ERROR"
    fields = {"transport_error": category}
    for attribute, field in (("errno", "os_errno"), ("verify_code", "certificate_verify_code")):
        value = getattr(cause, attribute, None)
        if type(value) is int and -65536 <= value <= 65536:
            fields[field] = value
    return fields


def runtime_fields():
    paths = ssl.get_default_verify_paths()
    return {"python_version": list(sys.version_info[:3]),
            "default_ca_file_readable": bool(paths.cafile and os.access(paths.cafile, os.R_OK)),
            "default_ca_directory_present": bool(paths.capath and os.path.isdir(paths.capath)),
            "ca_environment_overrides": {key: bool(os.environ.get(key)) for key in ("SSL_CERT_FILE", "SSL_CERT_DIR")}}


def check():
    # These are the only requests. No user URL, account/client/code/token, file,
    # browser cookie, environment credential or saved OAuth request is accepted.
    requests = (
        {"url": "https://api.accounts.untapped.gg/api/v1/account", "method": "GET", "headers": {}, "body": None},
        {"url": "https://api.accounts.untapped.gg/o/token", "method": "POST",
         "headers": {"Content-Type": "application/x-www-form-urlencoded"},
         "body": urlencode({"client_id": "harness-inert-client", "code": "harness-inert-code",
                            "code_verifier": "harness-inert-verifier", "grant_type": "authorization_code",
                            "redirect_uri": "http://localhost:17791/", "scope": "companion:full-access"})},
    )
    results = []
    for request in requests:
        route, url, headers, body = gateway._validate(request)
        row = {"route": route}
        try:
            status, returned, data = gateway._transport(request["method"], url, headers, body)
            kind = "OTHER"
            for name, value in returned.items():
                if name.lower() == "content-type":
                    media = value.split(";")[0].strip().lower()
                    kind = {"application/json": "JSON", "text/plain": "TEXT", "text/html": "HTML"}.get(media, "OTHER")
            row.update(status=status, response_kind=kind, body_bytes=len(data))
        except Exception as error:
            row.update(exception_fields(error))
            results.append(row)
            break
        results.append(row)
    return {"schema": 1, "mode": "FIXED_DATA_ACCOUNT_TRANSPORT_CHECK", "runtime": runtime_fields(),
            "results": results, "requests_attempted": len(results), "maximum_requests": 2,
            "real_credentials_sent": False, "cookies_sent": False, "app_launched": False,
            "raw_responses_included": False, "raw_errors_included": False}


def run():
    game_launch.test_identity("sts2test", game_launch.PROTECTED_HOME)
    safe = check()
    with tempfile.NamedTemporaryFile(prefix="sts2test-transport.", suffix=".json", dir="/private/tmp", delete=False) as output:
        output.write((json.dumps(safe, indent=2) + "\n").encode())
        os.fchmod(output.fileno(), 0o644)
    print("Diagnostic file: " + output.name)
    return safe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        print(json.dumps(run(), indent=2))
        return 0
    except Exception:
        print("Fixed-data transport check unavailable. Keep raw errors private.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
