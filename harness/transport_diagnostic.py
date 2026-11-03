"""Check the test account's HTTPS transport using fixed data and safe output."""

import argparse
import json
import os
import ssl
import sys
import tempfile
from urllib.parse import urlencode

from . import game_launch, gateway


exception_fields = gateway.exception_fields


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
