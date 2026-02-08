# Developer Setup

This runbook takes a new developer from empty machine to a working local stack.

## 1. Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- Git
- `uv` installed and available on `PATH`
- Optional native tools:
  - CMake
  - C++ compiler (MSVC/clang/gcc)
  - `clang-format`
  - `cppcheck`

## 2. Clone and bootstrap

```bash
git clone https://github.com/ringxworld/story_generator.git
cd story_generator
uv sync --all-groups
npm install --prefix web
```

If `uv` is not on your shell path, use local venv module execution:

```bash
.venv\Scripts\python.exe -m ruff --version
```

## 3. Install Git hooks

```bash
make hooks-install
```

This installs both `pre-commit` and `pre-push` checks.

## 4. Run the local stack

Terminal 1 (API):

```bash
make api
```

Terminal 2 (web studio):

```bash
make web-dev
```

Default local endpoints:

- API: `http://127.0.0.1:8000`
- Web: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/docs`

Default local DB:

- `work/local/story_gen.db`

Override DB path:

```bash
uv run story-api --db-path work/local/dev.db --reload
```

Override frontend API base URL:

```bash
# PowerShell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run --prefix web dev
```

## 5. Quality checks

Python quality:

```bash
make quality
```

Frontend quality:

```bash
make frontend-quality
```

Native quality:

```bash
make native-quality
```

Everything (local gate before push):

```bash
make check
```

## 6. Common workflows

Run tests only:

```bash
make test
make web-test
```

Auto-fix Python lint/format:

```bash
make fix
```

Build docs locally:

```bash
make docs-serve
make build-site
```

## 7. Optional NLP dependency groups

Install additional groups when needed:

```bash
uv sync --group nlp
uv sync --group topic
uv sync --group advanced
```

## 8. Troubleshooting

`uv: command not found`

- Re-open terminal after install.
- Confirm with `uv --version`.

`npm`/Node version mismatch

- Use Node 20+.
- Delete `web/node_modules` and run `npm install --prefix web`.

`cppcheck` or `clang-format` missing

- Install tooling locally, or skip native targets until installed.
- CI still enforces native checks.

Web cannot reach API

- Confirm API is running on `127.0.0.1:8000`.
- Verify `VITE_API_BASE_URL`.
- Check CORS origins in `STORY_GEN_CORS_ORIGINS` if customized.
