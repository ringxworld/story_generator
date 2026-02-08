# story_gen

`story_gen` is a Python project for writing stories with engineering-style controls to reduce drift.

## What this scaffold includes

- Domain concepts: `Theme`, `Character`, `Chapter`, `StoryBible`, `StoryState`
- Planning layer for chapter dependencies and concept mapping
- A simple CLI entry point
- Dependency charts in `docs/dependency_charts.md`
- Tests for the dependency validation logic

## Setup with uv

1. Install `uv`:
   - Windows PowerShell: `irm https://astral.sh/uv/install.ps1 | iex`
2. Ensure you have Python 3.11+ available.
3. Create and sync the environment:
   - `uv sync --all-groups`
4. Run tests:
   - `uv run pytest`
5. Run the CLI:
   - `uv run story-gen`

## Project layout

```text
.
|- docs/
|  \- dependency_charts.md
|- src/
|  \- story_gen/
|     |- application/
|     |- domain/
|     \- cli.py
|- tests/
|- pyproject.toml
\- README.md
```
