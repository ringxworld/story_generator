# Web Studio

The `web/` app is a React + TypeScript studio for creating and editing story
blueprints against the API contract.

## Offline demo on GitHub Pages

GitHub Pages now publishes a static offline demo build of the studio at:

- `https://ringxworld.github.io/story_generator/studio/`

This mode does not call the backend. It renders representative story analysis
dashboard data so visitors can explore the UX end-to-end.

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

To force offline mode locally for a static preview:

```bash
npm run --prefix web dev -- --host 127.0.0.1 --port 5173
# then open: http://127.0.0.1:5173/?demo=1
```

## Building blocks supported

- Story premise
- Canon rules
- Themes
- Characters
- Chapters and dependency references

The editor stores these as typed blueprint JSON so they are usable both by the
web studio and Python interfaces.
