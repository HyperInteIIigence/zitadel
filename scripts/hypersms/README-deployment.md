# HyperSMS Console deployment (ZITADEL v4.19.5)

The HTTP SMS test provider has already been registered inactive in the live
ZITADEL Admin API (ID `400389549018054661`).

## Release gates

1. Clone **exact** upstream tag `v4.19.5`, overlay **only** the reviewed
   `notification-sms-provider.component.html` and
   `notification-sms-provider.component.ts` from this PR.
2. Complete Console, generated assets, and Go API builds. Confirm
   `git diff --check` and review the two-file delta.
3. Build local image from `scripts/hypersms/Dockerfile.console-overlay`
   using the isolated source checkout as Docker build context.
4. Test image startup/version and compare with the working production image.
   Confirm all existing Compose configuration/secret references remain intact.
5. Check current login, API readiness and active SMS provider. Confirm
   independent rollback image locally available.
6. Install the override file into the existing
   `/HyperIntelligence/zitadel/zitadel-compose` deployment directory.
   Compose with existing base + existing override + the HyperSMS override,
   checking `config --quiet` before a service-only change. Keep the
   original ZITADEL login and database containers unchanged.
7. Check API readiness, HyperAccess login and SMS settings card; roll back
   immediately on failure. Do not activate this test provider.

### Rollback

Recreate **only** `zitadel-api` with the original base Compose and existing
static-IP override, excluding the HyperSMS image override. The original image
`ghcr.io/zitadel/zitadel:v4.19.5` must remain in the local image store.
Never prune, rewrite original Compose, restart PostgreSQL, or modify HyperAccess
credentials. This rollout has no database schema migrations.

### Operational status

Live provider registration completed. UI binary/image deployment requires
passing the build and acceptance checks. PlainApp GraphQL SMS bridge is not
implemented and the provider must remain inactive.
