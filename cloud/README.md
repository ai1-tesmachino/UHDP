# UHDP cloud service

The cloud API is an independent FastAPI process. It does not import the local
application, hardware discovery, HAL, or diagnostic executors. Store
`CLOUD_DATABASE_URL`, `CLOUD_JWT_SECRET`, and private object-storage credentials
in a protected cloud environment/secret manager; never put station tokens or
cloud secrets in frontend assets or the appliance image.

## Local cloud development

```bash
cd cloud
cp .env.example .env.cloud
# Edit .env.cloud and set a random POSTGRES_PASSWORD in that file.
docker compose --env-file .env.cloud up --build -d
docker compose --env-file .env.cloud exec cloud-api python -m cloud.admin create-company --name "Example Company"
```

Use the printed company ID to create a station and an initial administrator:

```bash
docker compose --env-file .env.cloud exec cloud-api python -m cloud.admin create-station --company-id COMPANY_ID --station-id STATION_ID --name "QC Station 1"
docker compose --env-file .env.cloud exec cloud-api python -m cloud.admin create-user --company-id COMPANY_ID --username admin@example.com --role administrator
```

The station token is printed once. Store it in the local appliance's protected
environment configuration. The user-creation command prompts for a password;
there is no self-registration endpoint.

For appliance sync, set `STORAGE_BACKEND=sqlite`, `CLOUD_API_URL` to the
HTTPS-reachable cloud API base URL, and `CLOUD_STATION_TOKEN` in the local
backend environment. Run the independent cloud service with:

```bash
uvicorn cloud.main:app --host 0.0.0.0 --port 8080
```

Use TLS at the cloud ingress, restrict PostgreSQL to the cloud private network,
use a private object bucket with lifecycle/backup policy, and provision
environment secrets from a secret manager in production. The development
compose file binds only to loopback and uses a named PostgreSQL volume.

## Security boundaries and limitations

User access tokens are signed, short-lived, and revalidated against active
tenant-scoped user records. Station bearer tokens are stored as SHA-256 hashes
and bound to a company/station; provisioning is an operator-only CLI operation.
Cloud record queries include the authenticated company ID. Event IDs are
idempotent and immutable QC revisions with same-revision divergent payloads are
preserved and flagged for supervisor review. Evidence is not marked synchronized
until object size and SHA-256 checksum headers are verified. A checksum detects
transfer corruption; it does not prove authenticity or prevent deliberate
tampering.

This initial cloud slice does not yet include token revocation/session storage,
login throttling, a web management UI, or Linux/deployed PostgreSQL/object-store
validation. Put rate limiting and TLS at the reverse proxy and rotate station
tokens by disabling/reprovisioning stations.

Back up the development PostgreSQL volume outside the container host using a
scheduled `pg_dump` process and test restores before relying on it; the compose
named volume alone is not a backup. For example:

```bash
docker compose --env-file .env.cloud exec -T postgres \
  pg_dump -U uhdp -d uhdp --format=custom > uhdp-cloud-$(date -u +%Y%m%dT%H%M%SZ).dump
```
