#!/usr/bin/env python3
"""Fail-closed production safeguard for the known disabled HyperSMS placeholder.

Reads ZITADEL admin credentials only from Phase-injected process env.
If and only if provider 400389549018054661 is ACTIVE while its endpoint
still equals the explicitly disabled placeholder, deactivate it via the
native Admin API; verify the resulting state. Do not touch any other
provider or change any configuration.
"""
import json
import os
import sys
import subprocess

ORIGIN = "https://gatekeeper.hyperintelligence.infrastructure"
ID = "400389549018054661"
DISABLED = "https://intelligence.hyperit.net.au/__hypersms/disabled"

def call(method, path, token):
    if not token or any(c in token for c in '\r\n"\\'):
        raise RuntimeError("Unsafe token format")
    # Pass the token to curl over stdin, not as argv or shell interpolation.
    config = 'header = "Authorization: Bearer ' + token + '"\n'
    proc = subprocess.run(
        ["curl", "--silent", "--show-error", "--fail", "--max-time", "10",
         "--max-redirs", "0", "--proto", "=https", "--request", method,
         "--header", "Content-Type: application/json", "--data-binary", "{}",
         "--config", "-", ORIGIN + path],
        input=config, text=True, capture_output=True, timeout=13,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin"}, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("ZITADEL HTTPS Admin API error, curl exit " + str(proc.returncode))
    return json.loads(proc.stdout) if proc.stdout.strip() else {}

def main():
    token = os.environ.get("ZITADEL_API_TOKEN", "")
    if not token:
        raise RuntimeError("Required Phase-injected Admin credential not available")
    result = call("POST", "/admin/v1/sms/_search", token)
    matches = [x for x in result.get("result", []) if x.get("id") == ID]
    if len(matches) != 1:
        raise RuntimeError("Expected one registered HyperSMS provider; refusing mutation")
    current = matches[0]
    state = current.get("state")
    endpoint = current.get("http", {}).get("endpoint")
    print("HYPERSMS_AUTHORITY_STATE", state)
    print("HYPERSMS_PLACEHOLDER_ENDPOINT", endpoint == DISABLED)
    if state in ("SMS_PROVIDER_CONFIG_ACTIVE", 1):
        if endpoint != DISABLED:
            raise RuntimeError("Active provider has real endpoint; no automatic mutation authorised")
        call("POST", "/admin/v1/sms/" + ID + "/_deactivate", token)
        after = call("POST", "/admin/v1/sms/_search", token)
        matches = [x for x in after.get("result", []) if x.get("id") == ID]
        if len(matches) != 1 or matches[0].get("state") not in ("SMS_PROVIDER_CONFIG_INACTIVE", 2):
            raise RuntimeError("Deactivation not verified; operator attention required")
        print("BROKEN_PLACEHOLDER_PROVIDER_DEACTIVATED_AND_VERIFIED")
    else:
        print("NO_MUTATION_PROVIDER_NOT_ACTIVE")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, KeyError, ValueError, subprocess.TimeoutExpired) as exc:
        print("HYPERSMS_SAFEGUARD_BLOCKED", type(exc).__name__, file=sys.stderr)
        sys.exit(1)
