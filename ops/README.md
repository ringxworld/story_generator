# Ops Scaffolding

This directory contains deployment-oriented templates for future hosted runs.

## Included

- `docker-compose.droplet.yml`
  - baseline multi-container stack for a single DigitalOcean Droplet
- `Caddyfile`
  - reverse-proxy template for TLS + API routing
- `.env.example`
  - expected environment keys for app/database/object storage

These files are scaffolds, not production-hardened manifests.
