# Ops Scaffolding

This directory contains deployment-oriented templates for future hosted runs.

## Included

- `docker-compose.droplet.yml`
  - baseline multi-container stack for a single DigitalOcean Droplet
- `docker-compose.aws.yml`
  - AWS-oriented compose scaffold (EC2/ECS-like host with optional local Postgres/MinIO fallback)
- `docker-compose.gcp.yml`
  - GCP-oriented compose scaffold (GCE/GKE-like host with optional local Postgres/MinIO fallback)
- `docker-compose.azure.yml`
  - Azure-oriented compose scaffold (VM/Container host with optional local Postgres/MinIO fallback)
- `Caddyfile`
  - reverse-proxy template for TLS + API routing
- `.env.example`
  - expected environment keys for app/database/object storage
- `.env.aws.example`, `.env.gcp.example`, `.env.azure.example`
  - provider-specific environment templates for the compose variants

These files are scaffolds, not production-hardened manifests.
