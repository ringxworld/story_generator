# Analysis Artifact Contracts (A-H)

These contract files define the expected output shape for the analysis stages
used by `story_gen`.

- `A_corpus_hygiene.json`
- `B_theme_motif.json`
- `C_voice_fingerprint.json`
- `D_character_consistency.json`
- `E_plot_causality.json`
- `F_canon_enforcement.json`
- `G_drift_robustness.json`
- `H_enrichment_data.json`

Each contract is intentionally lightweight and versioned so pipeline outputs can
be validated in CI or local checks before downstream use.
