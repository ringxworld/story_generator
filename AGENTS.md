# AGENTS.md

Project operating guide for coding agents working in `story_generator`.

## Mission

Build `story_gen` as a disciplined story-engineering project:
- stable canon and chapter dependencies
- strict quality gates
- reproducible workflows for reference analysis and publication

## Non-Negotiables

- Keep changes small, typed, and testable.
- Prefer strict typing over loose dictionaries.
- Do not weaken CI quality gates.
- Do not commit generated artifacts under `work/reference_data/` or `site/`.
- After each completed user prompt:
  1. commit
  2. push to `origin/main`

## Source of Truth Commands

Use `Makefile` targets instead of ad-hoc commands whenever possible:

- `make quality` -> lockfile check + lint + format-check + mypy + pytest
- `make hooks-install` -> install local pre-commit/pre-push gates
- `make hooks-run` -> run all configured hooks
- `make fix` -> auto-fix lint + format
- `make test` -> pytest
- `make build-site` -> build static site
- `make reference` -> run reference ingestion pipeline
- `make cpp-build` -> build native C++ tools
- `make cpp-test` -> run native C++ tests
- `make deploy` -> quality + site build + push

If `make` is unavailable in the local shell, run equivalent `uv` commands directly.

## Quality Gate Requirements

Any meaningful code change should pass:

1. `uv lock --check`
2. `uv run ruff check .`
3. `uv run ruff format --check .`
4. `uv run mypy`
5. `uv run pytest`

Local commit/push guardrails should be enabled via pre-commit:

- `pre-commit` stage: formatting/lint safeguards
- `pre-push` stage: `uv lock --check`, `mypy`, `pytest`

## Typing Standards

- Keep `mypy` strict-compatible (`pyproject.toml`).
- Prefer:
  - dataclasses for domain/config objects
  - `TypedDict` for serialized JSON payloads
  - explicit union/`Literal` types for option modes
- Avoid `Any` unless unavoidable and justified.

## CI/CD Expectations

- `CI` must remain the primary quality gate.
- Pages deployment should only run after successful CI on `main` (or explicit manual dispatch).
- If workflow changes are made, keep local commands and workflow steps aligned.

## Reference Pipeline Guardrails

- Respect crawl delay defaults and target-site policies.
- Keep reference ingestion for private analysis; avoid redistribution of full third-party text.
- Preserve cache behavior and deterministic outputs for tests.

## Native C++ Guardrails

- Use C++11+ and keep native tools focused on measurable hotspots.
- Keep Python as orchestrator; native binaries should be composable via CLI.
- If compiler toolchain is available, validate native changes with:
  1. `make cpp-configure`
  2. `make cpp-build`
  3. `make cpp-test`
  4. `make cpp-format-check`
  5. `make cpp-cppcheck`

## Documentation Maintenance

Update docs when behavior changes:

- `README.md` for project direction and high-level goals
- `docs/reference_pipeline.md` for ingestion workflow details
- `docs/dependency_charts.md` for architecture changes
- `docs/native_cpp.md` for native acceleration workflow

## Definition of Done (Per Prompt)

1. Implement requested change
2. Validate with quality gates relevant to scope
3. Summarize results concisely
4. Commit with a clear message
5. Push to `origin/main`
