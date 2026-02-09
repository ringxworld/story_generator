# Python API Reference

`story_gen` publishes two API documentation surfaces:

- Interactive HTTP API docs (local FastAPI runtime): `http://127.0.0.1:8000/docs`
- Hosted Python module reference (GitHub Pages): `https://ringxworld.github.io/story_generator/pydoc/`

The hosted Python reference is generated with `pdoc` during Pages deploy and is static.

## Local generation

From repository root:

```bash
uv run python tools/build_python_api_docs.py --output-dir pydoc_site
```

The helper script discovers all package modules under `src/story_gen/` and
builds a complete static reference set.
