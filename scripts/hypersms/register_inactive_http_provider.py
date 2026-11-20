#!/usr/bin/env python3
"""Register a harmless inactive HyperSMS/PlainApp HTTP SMS provider in ZITADEL.

Requires an explicitly authorised ZITADEL instance-admin token; never prints it.
Does not activate the provider, send SMS, or call PlainApp GraphQL.
"""
import argparse
import getpass
import json
import os
from pathlib import Path
import sys
import subprocess

DESCRIPTION = "HyperSMS / PlainApp (TEST - INACTIVE)"
API_ORIGIN = "https://gatekeeper.hyperintelligence.infrastructure"


def load_token(path):
    if path:
        token_file = Path(path)
        st = token_file.stat()
        if not token_file.is_file() or (st.st_mode & 0o077):
            raise RuntimeError("Token file must exist and be owner-only (mode 0600)")
        return token_file.read_text(encoding="utf-8").strip()
    # Phase CLI 'run' injects secrets into this process's environment.
    # Prefer the exact canonical Phase key; do not print or persist it.
    injected = os.environ.get("ZITADEL_API_TOKEN", "").strip()
    if injected:
        return injected
    return getpass.getpass("ZITADEL instance-admin access token (hidden): ").strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Create one inactive test provider")
    parser.add_argument("--token-file", default=os.getenv("ZITADEL_SMS_ADMIN_TOKEN_FILE"))
    parser.add_argument("--ca-file", default=os.getenv("ZITADEL_SMS_CA_FILE"))
    args = parser.parse_args()

    token = load_token(args.token_file)
    if not token:
        raise RuntimeError("Authorised instance-admin token missing")

    # curl validates server TLS using the host's configured trust store.
    # Pass the bearer header through stdin (--config -), never an argv value.
    # Do not expose other Phase-injected secrets in the curl child environment.
    if any(char in token for char in ('\r', '\n', '\x00', '"', '\\')):
        raise RuntimeError("Unsafe credential characters")

    def post(path, data):
        url = API_ORIGIN + path
        cmd = [
            "curl", "--silent", "--show-error",
            "--max-time", "12", "--max-redirs", "0", "--proto", "=https",
            "--request", "POST", "--config", "-",
            "--header", "Content-Type: application/json",
            "--header", "Accept: application/json",
            "--data-binary", json.dumps(data, separators=(",", ":")),
            "--write-out", "\nHYPERSMS_HTTP_STATUS:%{http_code}",
            url,
        ]
        if args.ca_file:
            cmd.extend(["--cacert", args.ca_file])
        proc = subprocess.run(
            cmd,
            input='header = "Authorization: Bearer ' + token + '"\n',
            capture_output=True,
            text=True,
            timeout=16,
            check=False,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        )
        marker = "\nHYPERSMS_HTTP_STATUS:"
        if marker not in proc.stdout:
            raise RuntimeError("Verified ZITADEL API request failed (no status)")
        body, status = proc.stdout.rsplit(marker, 1)
        if proc.returncode != 0 or status.strip() != "200":
            raise RuntimeError("ZITADEL API request rejected: HTTP " + status.strip())
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise RuntimeError("ZITADEL API returned malformed JSON") from None

    def inventory():
        response = post("/admin/v1/sms/_search", {})
        providers = response.get("result", [])
        if not isinstance(providers, list):
            raise RuntimeError("Unexpected SMS provider list format")
        details = response.get("details", {})
        reported_total = int(details.get("totalResult", len(providers)))
        if reported_total > len(providers):
            raise RuntimeError("Provider listing incomplete; refusing duplicate creation")
        return providers

    matches = [p for p in inventory() if p.get("description") == DESCRIPTION]
    if len(matches) > 1:
        raise RuntimeError("Duplicate HyperSMS test providers; manual reconciliation needed")
    if matches:
        provider = matches[0]
        if not provider.get("http"):
            raise RuntimeError("Matching name belongs to a non-HTTP provider")
        if provider.get("state") != "SMS_PROVIDER_CONFIG_INACTIVE":
            raise RuntimeError("Matching provider is not inactive; refusing to modify")
        if provider.get("http", {}).get("endpoint"):
            raise RuntimeError("Matching provider has a configured endpoint; refusing to modify")
        print("EXISTING_INACTIVE_PROVIDER", provider.get("id"))
        return 0
    if not args.apply:
        print("DRY_RUN: would create inactive test HTTP SMS provider; no changes made")
        return 0

    created = post("/admin/v1/sms/http", {"description": DESCRIPTION, "endpoint": ""})
    provider_id = created.get("id")
    if not provider_id:
        raise RuntimeError("Create response did not return a provider ID")
    # Never print 'created': it contains a generated signing key.
    updated = [p for p in inventory() if p.get("id") == provider_id]
    if len(updated) != 1 or not updated[0].get("http"):
        raise RuntimeError("Created provider cannot be verified via list")
    provider = updated[0]
    if provider.get("state") != "SMS_PROVIDER_CONFIG_INACTIVE":
        raise RuntimeError("CRITICAL: provider unexpectedly active; investigate before proceeding")
    if provider.get("http", {}).get("endpoint"):
        raise RuntimeError("CRITICAL: test provider has unexpected endpoint")
    print("CREATED_AND_VERIFIED_INACTIVE_PROVIDER", provider_id)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        sys.exit(1)
