# Contracts Registry

This project tracks schema and pipeline contracts in one versioned registry.

## Source of truth

- Runtime registry model:
  - `src/story_gen/api/contract_registry.py`
- Exported snapshot (versioned artifact):
  - `work/contracts/story_pipeline_contract_registry.v1.json`

## Update workflow

When you add or change a schema or pipeline stage contract:

1. Update `src/story_gen/api/contract_registry.py`.
2. If stage boundaries changed, update `src/story_gen/core/pipeline_contracts.py`.
3. Regenerate snapshot:

```bash
make contracts-export
```

4. Run checks:

```bash
uv run python tools/check_contract_drift.py
uv run pytest tests/test_contract_registry.py
uv run pytest tests/test_story_analysis_pipeline.py
```

## What this prevents

- Silent drift between code and docs around contract ownership.
- Pipeline stage changes that are not explicitly tracked.
- Ambiguous schema version usage across API and core pipeline artifacts.
