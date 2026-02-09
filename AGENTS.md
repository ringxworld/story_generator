# AGENTS.md

Repository operating rules for coding agents.

## 0. Prime Directive

- You may generate code quickly.
- You may not change architecture without explicit approval.
- If a requested change violates repository contracts, stop and ask for clarification.
- Prefer correctness and boundary integrity over speed.

## 1. Required Repository Contracts

These artifacts must remain present:

- `LICENSE`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CODEOWNERS`
- `docs/architecture.md`
- `docs/adr/`

If a change introduces new public behavior or a new dependency, add an ADR.

## 2. Module Ownership and Boundaries

Python ownership model:

- `src/story_gen/api/` -> public API layer
- `src/story_gen/core/` -> internal logic
- `src/story_gen/adapters/` -> side effects / IO
- `src/story_gen/native/` -> native binding boundary
- `src/story_gen/cli/` -> argparse command entrypoints

Import rules:

- `api` may import `core`, `adapters`, `native`
- `core` must not import `api`, `adapters`, `native`
- `adapters` must not be imported by `core`
- only `native` may import compiled extension modules

## 3. Python / C++ Boundary Rules

- C++ source: `cpp/`
- Public C++ headers: `cpp/include/`
- Binding code: `bindings/` or `src/story_gen/native/`
- C++ must not include Python headers outside binding code
- Python must not expose raw-pointer ownership semantics

## 4. Quality and Enforcement

Expected checks:

- `uv lock --check`
- `uv run python tools/check_imports.py`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy`
- `uv run pytest`
- `uv run mkdocs build --strict`

Do not bypass pre-commit or CI.
Do not remove tests to satisfy gates. Add or adjust tests to validate both
working paths and failure paths of the behavior under test.

## 5. Entropy Prevention

- No `utils` module names.
- No `TODO` without issue reference (example: `TODO(#123): ...`).
- No new public API without docs and tests.
- Feature flags require explicit removal plan.

## 6. ADR Discipline

Before non-trivial implementation, add/update ADR with:

- Problem
- Non-goals
- Public API
- Invariants
- Test plan

## 7. Completion Rule

After each completed prompt:

1. implement
2. validate
3. commit
4. push to `origin/main`

## 8. Human-Facing Wording for Issues and PRs

When writing issue or PR text:

- Use human, specific language over boilerplate.
- Prefer concrete sentences about intent and impact.
- Avoid templated phrases like "This change does X" when a more natural sentence works.
- Link issues with full URLs, not just `#123`.
- State tradeoffs and test coverage explicitly, without hedging.

## 9. Human-Facing PR Reviews

When commenting or reviewing pull requests:

- Use normal paragraph spacing and complete sentences.
- Lead with the most important finding, then explain why it matters.
- Avoid robotic checklists unless the author asked for one.
- Call out missing tests and edge cases in plain language.

## 10. PR Body Flexibility and Reviewer Assignment

When creating PRs:

- Use the full PR structure for large or risky work.
- Use a compact PR structure for docs/chore/small-scope work when context can be concise.
- Always include `Summary` and `Linked Issues`.
- Request reviewer `ringxworld` by default (or assign as assignee when self-review is blocked).
