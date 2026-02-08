# Web Studio

The `web/` app is a React + TypeScript studio for creating and editing story
blueprints against the API contract.

## Run locally

1. Start API:

```bash
uv run story-api --host 127.0.0.1 --port 8000 --reload
```

2. Start frontend:

```bash
npm install --prefix web
npm run --prefix web dev
```

3. Open the printed Vite URL (usually `http://127.0.0.1:5173`).

## API base URL

Set `VITE_API_BASE_URL` when frontend and API are not on default local ports.

Example:

```bash
$env:VITE_API_BASE_URL="http://127.0.0.1:8001"
npm run --prefix web dev
```

## Building blocks supported

- Story premise
- Canon rules
- Themes
- Characters
- Chapters and dependency references

The editor stores these as typed blueprint JSON so they are usable both by the
web studio and Python interfaces.
