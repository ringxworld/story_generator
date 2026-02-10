# API

The HTTP API is defined by FastAPI and exported as OpenAPI.

## Source of Truth

- Runtime Swagger UI (interactive): `http://127.0.0.1:8000/docs`
- Runtime ReDoc (interactive): `http://127.0.0.1:8000/redoc`
- Runtime OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Hosted static OpenAPI JSON (Pages docs snapshot): `https://ringxworld.github.io/story_generator/docs/assets/openapi/story_gen.openapi.json`

## Hosted API Reference (Static)

The docs site renders the exported OpenAPI schema using ReDoc:

<div id="redoc-container"></div>
<script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
<script>
  const specUrl = new URL('../assets/openapi/story_gen.openapi.json', window.location.href).toString();
  Redoc.init(specUrl, {
    expandResponses: '200,201',
    hideDownloadButton: false,
    sortPropsAlphabetically: true
  }, document.getElementById('redoc-container'));
</script>

## Local run

```bash
uv run story-api --host 127.0.0.1 --port 8000 --reload
```

Custom database path:

```bash
uv run story-api --db-path work/local/story_gen.db
```

## Authentication in Swagger UI

1. Call `POST /api/v1/auth/register` or use an existing account.
2. Call `POST /api/v1/auth/login` and copy `access_token`.
3. Click **Authorize** in Swagger UI and paste `Bearer <token>`.
4. Execute owner-scoped routes (`/stories/*`, `/essays/*`).

## Keep docs current

Generate the committed OpenAPI snapshot used by docs:

```bash
make openapi-export
```

Check for schema drift in CI/local gates:

```bash
make openapi-check
```

## Python API docs

Python module docs are published separately:

- Hosted Python API reference: `https://ringxworld.github.io/story_generator/pydoc/`
- Local build: `uv run python tools/build_python_api_docs.py --output-dir pydoc_site`

## Notes

- GitHub Pages is static hosting and cannot run live FastAPI routes.
- The interactive Swagger/ReDoc surfaces require a running API process.
