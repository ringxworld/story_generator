# Storage Decision Matrix

This document records the decision spike for
https://github.com/ringxworld/story_generator/issues/97 and feeds the broader
storage-direction roadmap in https://github.com/ringxworld/story_generator/issues/11.

## Benchmark Method

- Command:
  `uv run python tools/storage_decision_benchmark.py`
- Dataset config:
  - stories: `600`
  - operations per query: `2500`
  - seed: `104729`
- Output artifact:
  `work/benchmarks/storage_decision_spike.v1.json`

Representative query set:

- latest analysis lookup (`owner_id + story_id`)
- theme-to-beat relation lookup
- two-hop neighborhood context lookup

## Measured Latency (Microseconds)

| Query | Model | p50 | p95 | mean | max |
| --- | --- | ---: | ---: | ---: | ---: |
| latest_story_lookup | mongo_style_document | 0.2 | 0.3 | 0.215 | 3.5 |
| latest_story_lookup | graph_indexed | 0.2 | 0.4 | 0.261 | 4.5 |
| related_beats_for_theme | mongo_style_document | 6.5 | 10.9 | 7.008 | 54.9 |
| related_beats_for_theme | graph_indexed | 3.0 | 6.8 | 3.47 | 28.3 |
| two_hop_context | mongo_style_document | 13.5 | 16.1 | 14.403 | 76.1 |
| two_hop_context | graph_indexed | 4.2 | 5.8 | 4.205 | 14.9 |

Interpretation:

- Point lookups are effectively equal for both models.
- Graph-indexed traversal is materially faster for relation-heavy and multi-hop queries.
- Traversal advantage appears at current workload shape, but this benchmark is
  in-process prototype data, not managed-service latency.

## Cost and Complexity Tradeoff

| Option | Latency Profile | Infra Cost | Engineering Complexity | Recommendation |
| --- | --- | --- | --- | --- |
| SQLite JSON (current default) | Strong for point reads, weaker for deep traversal | Lowest | Lowest | Keep default for local/dev and baseline CI |
| Mongo-style document model | Similar point reads, moderate traversal cost | Low to medium | Medium | Preferred first scaling step for persisted artifacts |
| Graph-indexed model / graph DB path | Best traversal and neighborhood queries | Medium to high | Highest | Adopt only when traversal SLOs justify infra and ops burden |

## Recommendation

1. Keep `sqlite` as default in local and CI paths.
2. Preserve the new adapter boundary with `mongo-prototype` and
   `graph-prototype` behind explicit feature flags.
3. Prioritize document-model migration first when analysis payload size and read
   concurrency exceed current SQLite comfort limits.
4. Promote graph-native backend only when traversal-heavy SLOs require it.

## Migration and Rollback Notes

Forward path:

1. Run dual-write in staging (`sqlite` + selected prototype backend).
2. Verify API response parity with contract drift checks and endpoint tests.
3. Cut reads to selected backend after parity and backup verification.

Rollback path:

1. Switch `STORY_GEN_ANALYSIS_BACKEND=sqlite`.
2. Disable prototype feature flag (`STORY_GEN_ENABLE_*_ADAPTER=0` or unset).
3. Restart API/CLI workers.
4. Re-run contract drift + API smoke checks before resuming traffic.
