# Work Directory

This directory is for local research artifacts and literary analysis work.

## Layout

- `resources/`: stable templates and notes you maintain in git
- `reference_data/`: generated chapter dumps, translations, and reports (ignored by git)

## Suggested workflow

1. Update `resources/focus_names.txt` with characters you want tracked.
2. Run `uv run story-reference ...` to ingest chapters.
3. Review:
   - `work/reference_data/<project>/samples/story_sample.md`
   - `work/reference_data/<project>/analysis/analysis.md`
4. Extract transferable insights into your own story spec.
