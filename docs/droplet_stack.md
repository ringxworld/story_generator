# Droplet Stack (Planned)

This project is intentionally steering toward a budget-conscious deployment
model before any enterprise cloud footprint.

## Target shape

- one DigitalOcean Droplet
- FastAPI backend container
- Postgres container
- MinIO container (S3-compatible object storage)
- Caddy reverse proxy
- GitHub Pages for static docs/front-end

## Repository scaffolding

- `ops/docker-compose.droplet.yml`
- `ops/.env.example`
- `ops/Caddyfile`

## Why this path

- predictable cost profile for early stages
- no lock-in to proprietary storage APIs
- straightforward migration path to managed services later
