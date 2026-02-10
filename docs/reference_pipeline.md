# Reference Pipeline

This pipeline is for private literary analysis using publicly readable reference text.

## Run crawl + analysis

```bash
uv run story-reference --max-episodes 20
```

Outputs are written under:

- `work/reference_data/n2267be/meta/index.json`
- `work/reference_data/n2267be/raw/*.json`
- `work/reference_data/n2267be/samples/story_sample.md`
- `work/reference_data/n2267be/analysis/analysis.json`
- `work/reference_data/n2267be/analysis/analysis.md`

## Translate with LibreTranslate

Run your own local LibreTranslate service first, then:

```bash
uv run story-reference \
  --translate-provider libretranslate \
  --libretranslate-url http://localhost:5000 \
  --max-episodes 3
```

## Offline translation

Install the optional group:

```bash
uv sync --group translation
```

Then run with:

```bash
uv run story-reference --translate-provider argos --max-episodes 3
```

Use `--translate-provider chain` to try Argos first and fall back to LibreTranslate.

## Batch pipeline runner

For chapter text files on disk, use the batch pipeline:

```bash
uv run story-pipeline-batch \
  --source-dir work/resources/re_zero/n2267be/chapters \
  --run-id re-zero \
  --translate-provider none \
  --mode analyze
```

Outputs land in `work/pipeline_runs/re-zero/` with per-chapter summaries and a
`summary.json` timing report.

## Focus names for character tracking

Edit:

- `work/resources/focus_names.txt`

Then re-run the pipeline to refresh mention counts in analysis output.

## Politeness and usage

- Default crawl delay is `1.1s`.
- Keep this for local reference and study.
- Avoid redistributing full third-party text.
