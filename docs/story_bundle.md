# Story Bundle (`.sgb`)

Story bundle is a portable binary container for sharing complete story analysis
artifacts without shipping loose JSON files.

## Why use it

- single file for export/import workflows
- compressed payload (zlib) for smaller transfers
- strong integrity checks (manifest + payload + per-record hashes)
- explicit schema versioning for safe evolution

## Included records in `story_bundle.v1`

- `story_document.json`
- `dashboard_read_model.json`
- `timeline_actual.json`
- `timeline_narrative.json`
- `segment_alignments.json`
- `arc_signals.json`
- `conflict_shifts.json`
- `emotion_signals.json`
- `evaluation_metrics.json`
- `graph.svg`

## Binary envelope layout

1. Header
2. JSON manifest
3. zlib-compressed payload bytes
4. Trailer checksums

Header fields:

- magic: `SGBN`
- format version: `1`
- manifest length
- compressed payload length

Trailer fields:

- SHA-256(manifest bytes)
- SHA-256(compressed payload bytes)

## Python usage

```python
from story_gen.core.story_analysis_pipeline import run_story_analysis
from story_gen.core.story_bundle import pack_story_analysis_bundle, unpack_story_analysis_bundle

result = run_story_analysis(story_id="story-1", source_text="...")
bundle_bytes = pack_story_analysis_bundle(result=result)

loaded = unpack_story_analysis_bundle(bundle_bytes)
assert loaded.story_document.story_id == "story-1"
```

## Notes for collaboration roadmap

- `.sgb` is ideal for snapshot/export and handoff workflows.
- Real-time collaboration state (presence, cursors, transient selections) should
  stay outside bundle payloads and be synchronized separately.
