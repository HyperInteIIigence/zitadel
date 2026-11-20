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
import ssl
import sys
import urllib.error
import urllib.request

ORIGIN = "https://gatekeeper.hyperintelligence.infrastructure"
ID = "400389549018054661"
DISABLED = "https://intelligence.hyperit.net.au/__hypersms/disabled"

def call(method, path, token):
    req = urllib.request.Request(
        ORIGIN + path,
        method=method,
        data=b"{}",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10, context=ssl.create_default_context()) as res:
        if res.status < 200 or res.status >= 300:
            raise RuntimeError("Unexpected ZITADEL API response")
        raw = res.read(131072)
    return json.loads(raw) if raw else {}

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
    except (RuntimeError, KeyError, ValueError, urllib.error.URLError) as exc:
        print("HYPERSMS_SAFEGUARD_BLOCKED", type(exc).__name__, file=sys.stderr)
        sys.exit(1)
