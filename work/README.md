# Work Directory

This directory is for local research artifacts and literary analysis work.

## Layout

- `resources/`: stable templates and notes you maintain in git
- `contracts/`: analysis artifact contracts (A-H) for pipeline outputs
- `reference_data/`: generated chapter dumps, translations, and reports (ignored by git)

## Current resources

- `work/resources/literary_lens.md`: reusable chapter review checklist
- `work/resources/focus_names.txt`: tracked names for mention analysis
- `work/resources/kingdom_hearts_metaphysics.md`: thematic reference model for meaning, participation, and world-coherence design
- `work/contracts/README.md`: A-H artifact contract scaffold and usage notes

## Suggested workflow

1. Update `resources/focus_names.txt` with characters you want tracked.
2. Run `uv run story-reference ...` to ingest chapters.
3. Review:
   - `work/reference_data/<project>/samples/story_sample.md`
   - `work/reference_data/<project>/analysis/analysis.md`
4. Extract transferable insights into your own story spec.
