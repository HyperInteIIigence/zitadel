# HyperSMS Console — ZITADEL v4.19.5 deployment record

## Production state (20 November 2026)

**DEPLOYED — UI only; SMS sending disabled.**

- Native HTTP SMS provider ID: `400389549018054661`
- Description: `HyperSMS / PlainApp (TEST - INACTIVE)`
- State: `SMS_PROVIDER_CONFIG_INACTIVE` (verified after deployment using Phase-injected ZITADEL API token)
- Endpoint: `https://intelligence.hyperit.net.au/__hypersms/disabled`, protected by a route returning HTTP 403 for unauthenticated requests
- API container image: `hypersms-zitadel:4.19.5-console-20261120`
- Image digest/ID: `sha256:4435734535e1211ec0758b314938c7bb8fe189b8465c409431a634e28f552881`
- Base image retained locally: `ghcr.io/zitadel/zitadel:v4.19.5`, ID `sha256:5fdb16da5ceb31a7dfddfade6a3f19c4800a591f4e76a0e4863a30033dd1a532`
- Upstream source tag: `v4.19.5`, commit `a618740b578627b7b9acbbb111a6948882d6f5dc`
- Only two Console source files were overlaid in an isolated source tree.
- Go/Angular build completed; both base and custom image report `zitadel version v4.19.5`.
- Production Docker Compose `zitadel-api` was recreated **alone**; API and login and postgres health checks were healthy; Console HTTPS returned 200.
- Live Console served the updated `chunk-E6PK4IDQ.js` and it matched the built artifact byte-for-byte. The open ZITADEL management tab showed `HTTP · HyperSMS / PlainApp (TEST - INACTIVE)` beside Twilio.

## Persistent deployment configuration

The standard on-host Compose files are:

```text
/HyperIntelligence/zitadel/zitadel-compose/docker-compose.yml
/HyperIntelligence/zitadel/zitadel-compose/docker-compose.override.yml
```

The second file contains the existing fixed-IP mappings and now also contains **only one new operational field**, under `zitadel-api`:

```yaml
    image: hypersms-zitadel:4.19.5-console-20261120
```

Before this change, a byte-identical copy of the existing override was saved at:

```text
/HyperIntelligence/zitadel/zitadel-compose/docker-compose.override.yml.pre-hypersms-20261120
```

Subsequent default Compose invocations using the base and standard override resolve to the HyperSMS image without requiring a temporary `/tmp` overlay. The combined Compose configuration validated via `config --quiet`. A complete Windmill reboot has **not** been tested as part of this change.

## Reproducible build requirements

Use the exact upstream v4.19.5 tag and apply only the two reviewed source edits from this PR. Generated frontend assets are embedded in the Go server binary, therefore a Console-only build is insufficient. Run `@zitadel/console:build` and `@zitadel/api:build-linux` from the isolated checkout with pinned pnpm 10.30.3.

The initial Go build lacked release-version metadata. A subsequent targeted Go build injected the exact release version `v4.19.5`, upstream commit and an RFC3339 build date via `-ldflags -X` for `github.com/zitadel/zitadel/cmd/build.version`, `cmd/build.commit` and `cmd/build.date`. **Retain these flags** on every rebuild; a binary reporting the current timestamp as its version is not acceptable for deployment.

Create the runtime image with `scripts/hypersms/Dockerfile.console-overlay` from the isolated checkout after the version-matched binary passes `--version` verification. Retain the base image and perform a service-only rollout with rollback protection.

## Rollback (restores the exact previous Compose override)

1. Check that the original `ghcr.io/zitadel/zitadel:v4.19.5` image is still available.
2. Restore `docker-compose.override.yml` from the `.pre-hypersms-20261120` backup above. **Do not remove its static-IP assignments**.
3. Validate the restored base + override configuration with `docker compose ... config --quiet`.
4. Recreate **only** the `zitadel-api` service using the restored base + default override. Do not recreate `zitadel-login`, proxy, PostgreSQL or their networks.
5. Confirm API readiness, authentication functions and SMS provider settings. The API provider record remains inactive and unchanged.

Never prune, modify provider activation, reset certificates, or migrate the database for this UI-only change.

## Security and feature boundary

The Phase secret `ZITADEL_API_TOKEN` was injected from application `HyperIntelligence`, environment `Production`, path `/integrations/mcp/provider-readonly`. The credential **can create SMS providers** despite the read-only-labelled path; audit its account permissions and adopt a narrower administrative credential. No token values were committed or logged.

**PlainApp GraphQL is not connected.** There is no production HyperSMS webhook-to-GraphQL bridge and no SMS sending or delivery verification in scope. Keep this test provider inactive until the adapter, replay protection, signature checks and controlled end-to-end testing are complete.
