# story_gen

`story_gen` is a Python project for writing stories with engineering-style controls to reduce drift.

## What this scaffold includes

- Domain concepts: `Theme`, `Character`, `Chapter`, `StoryBible`, `StoryState`
- Planning layer for chapter dependencies and concept mapping
- A simple CLI entry point
- Dependency charts in `docs/dependency_charts.md`
- Tests for the dependency validation logic
- GitHub Actions CI (`.github/workflows/ci.yml`)
- GitHub Pages deployment workflow (`.github/workflows/deploy-pages.yml`)

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
6. Build the static story page locally:
   - `uv run python scripts/build_story_site.py`
7. Ingest a reference story for analysis:
   - `uv run story-reference --max-episodes 3 --sample-count 2`

## Project layout

```text
.
|- .github/workflows/
|  |- ci.yml
|  \- deploy-pages.yml
|- content/
|  \- story.md
|- docs/
|  \- dependency_charts.md
|- scripts/
|  \- build_story_site.py
|- src/
|  \- story_gen/
|     |- application/
|     |- domain/
|     \- cli.py
|- tests/
|- pyproject.toml
\- README.md
```

## CI/CD with GitHub

- `CI` workflow runs on pushes to `main` and pull requests.
- Checks executed:
  - `ruff check .`
  - `mypy`
  - `pytest`

## GitHub Pages deployment

The deployment workflow builds `content/story.md` into `site/index.html` and publishes it.

1. In GitHub repository settings, go to `Pages`.
2. Set `Source` to `GitHub Actions`.
3. Commit updates to `content/story.md` and push to `main`, or trigger `Deploy Story Site` manually from Actions.
4. After deployment, your site will be available at:
   - `https://ringxworld.github.io/story_generator/`

## Reference Story Pipeline

Use this for private literary analysis workflows.

- Default source: `https://ncode.syosetu.com/n2267be/`
- Output root: `work/reference_data/<project-id>/`

### Example commands

- Crawl and analyze first 10 episodes (no translation):
  - `uv run story-reference --max-episodes 10`
- Crawl a specific episode range:
  - `uv run story-reference --episode-start 1 --episode-end 20`
- Enable translation with a local LibreTranslate server:
  - `uv run story-reference --translate-provider libretranslate --libretranslate-url http://localhost:5000 --max-episodes 3`

### Notes

- The script respects crawl delay defaults (`1.1s`) based on `robots.txt`.
- Keep generated reference data local; avoid redistributing full third-party text.
- Detailed usage: `docs/reference_pipeline.md`
