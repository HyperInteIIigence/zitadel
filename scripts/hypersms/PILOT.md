# HyperSMS / PlainApp pilot (non-production SMS testing)

## Gate 0 — editable Console
ZITADEL v4.19.5 has a native HTTP provider (ID `400389549018054661`).
The Console includes an edit dialog for description and the HTTPS webhook
on `https://intelligence.hyperit.net.au/__hypersms/`.
It does **not** configure PlainApp GraphQL credentials and must not display
one in a browser. Editing the webhook does not send an SMS.

**The ZITADEL provider must remain INACTIVE until the relay proves safe.**
ZITADEL has a single active provider per instance, so activation would affect
actual user OTPs.

## Gate 1 — establish private PlainApp compatibility
- Confirm the actual PlainApp version/GraphQL schema on the Android handset.
- Verify the `sendSms` mutation, `requiresConfirmation` and
  `smsSendResult` subscription against the installed build.
- Use a dedicated phone/SIM for pilot and secure the Phone/GraphQL API tokens
  in Phase; do not put them in ZITADEL Console fields or repository files.
- Confirm unattended sends are possible; if Android requires per-message user
  confirmation, don't enable it for authentication.
- Keep the mobile service private; no direct inbound public HTTPS to phone.

## Gate 2 — implement and independently test Go relay
- Webhook listener receives ZITADEL's original signed raw HTTP request,
  verifies its HMAC-SHA256 timestamp/signature using a Phase-stored key.
- Reject unknown event types and number formats; allowlist only *explicitly
  approved* Australian test destination numbers; never record OTP contents.
- Implement replay protection and persistent request deduplication across
  process restarts. Enforce per-number and global send limits.
- Connect to PlainApp using TLS verification and tightly scoped credentials,
  with bounded send timeouts and a persistent status machine.
- Treat accepted GraphQL requests, `requiresConfirmation`, and eventual SMS
  result separately. A GraphQL acknowledgement is not handset/carrier delivery.
- Fail closed on expiry, invalid signatures, external URLs or network loss.

## Gate 3 — isolated pilot
- Exercise signed synthetic test requests against the relay and private
  handset, **not ZITADEL's production OTP provider**.
- Send at most one consented test SMS, using the approved test number,
  then verify acknowledgement and device/carrier result.
- Confirm duplicate suppression, wrong signatures, wrong number, timeout,
  phone offline and token revoked failures.
- Conduct a negative test proving no production user number is accepted.

## Gate 4 — optional production change
Requires independent owner acceptance, complete end-to-end delivery and
rollback tests, tested recovery login, and a reviewed credential model.
Only then consider switching the active SMS provider. That switch is global,
not per test account. It cannot be advertised as pilot-only unless run on
an isolated ZITADEL instance.

## Rollback
1. Restore the previous `docker-compose.override.yml` backup and its original
   API image selection, without changing static-IP addresses.
2. Recreate only `zitadel-api` and verify login, API health, SMS settings.
3. Leave current SMS provider activation unchanged.
