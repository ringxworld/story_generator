# ADR 0002: Phased NLP Stack and A-H Analysis Artifact Contracts

## Status

Accepted

## Problem

We need stronger analysis capabilities for reference corpora, but adding too
many probabilistic tools at once increases CI instability and operational
complexity. We also need a stable artifact contract so analysis outputs can be
validated and consumed consistently.

## Non-goals

- Full production implementation of every analysis stage in this ADR.
- Immediate adoption of heavyweight optional systems (graph databases,
  legacy NLP stacks).

## Decision

Adopt a phased tool stack and scaffold contracts for analysis stages A-H.

Phase 1 dependencies:

- `spacy` for tokenization/POS/NER/sentence boundaries
- `sentence-transformers` for embeddings and drift checks
- `networkx` for canon/entity/event graphs

Phase 2 dependencies:

- `bertopic` with `umap-learn` + `hdbscan` for topic/motif discovery once
  corpus segmentation is stable
- `stanza` only as an optional second-opinion parser/lemmatizer

Explicitly deferred:

- `allennlp` (stale for this use case and harder to maintain)
- `neo4j` (defer until in-memory/file graph storage is insufficient)

Add scaffolded artifact contract files under `work/contracts/` for:

- A. corpus hygiene and segmentation
- B. theme and motif extraction
- C. voice/style fingerprinting
- D. character voice consistency
- E. plot and causality structure
- F. canon and contradiction checks
- G. drift/robustness evaluation
- H. enrichment data for future calibration

## Public API

No runtime public API behavior change. This introduces dependency groups and
contract artifacts for internal analysis workflows.

## Invariants

- Deterministic contradiction/canon validators remain primary truth checks.
- Probabilistic analysis outputs must map back to segment IDs.
- Contract file schema remains JSON and human-editable.

## Test plan

- Contract tests assert dependency groups (`nlp`, `topic`, `advanced`) exist.
- Contract tests assert all A-H contract files exist and are valid JSON.
- Existing CI quality gates remain unchanged.
