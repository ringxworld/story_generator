# story_gen

[![CI](https://github.com/ringxworld/story_generator/actions/workflows/ci.yml/badge.svg)](https://github.com/ringxworld/story_generator/actions/workflows/ci.yml)
[![Deploy Pages](https://github.com/ringxworld/story_generator/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/ringxworld/story_generator/actions/workflows/deploy-pages.yml)

A story engineering project for building original fiction with discipline.

We are treating storytelling like a software system: define canon, model dependencies, validate continuity, and evolve chapters without drift.

Live project pages:
- https://ringxworld.github.io/story_generator/

## Current Stage

- Build the core story engine around themes, chapters, characters, and canon.
- Use reference-text analysis to learn craft patterns (structure, dialogue, pacing, character pressure).
- Turn those patterns into reusable constraints for original story generation.

## What This Project Is Optimizing For

- Narrative consistency over long arcs
- Intentional character voice and relationship evolution
- Clear chapter-level objectives and dependency tracking
- Repeatable workflow from draft to validated chapter

## Working Principles

- Canon is explicit and versioned.
- Drift checks are automated and test-backed.
- Reference material is for private study, not redistribution.
- Every change should move us toward a reliable, high-quality story pipeline.

## Focus Areas

- Architecture contracts: `docs/architecture.md`
- Visual architecture diagrams: `docs/architecture_diagrams.md`
- ADR records: `docs/adr/`
- Story model and planning architecture: `docs/dependency_charts.md`
- Reference ingestion + analysis workflow: `docs/reference_pipeline.md`
- Native acceleration path (C++/CMake): `docs/native_cpp.md`
- Deployment split (Pages + API): `docs/deployment.md`
- Planned DigitalOcean deployment baseline: `docs/droplet_stack.md`
- Developer local setup runbook: `docs/developer_setup.md`
- React + TypeScript story studio: `docs/studio.md`
- Story-first feature extraction pipeline: `docs/feature_pipeline.md`
- Full-series text collection: `src/story_gen/cli/story_collector.py`
- Video-story transcript ingestion: `src/story_gen/cli/youtube_downloader.py`
- HTTP API local-preview boundary: `src/story_gen/api/app.py`
- Python blueprint interface: `src/story_gen/api/python_interface.py`

## Governance

- Contribution process: `CONTRIBUTING.md`
- Security reporting: `SECURITY.md`
