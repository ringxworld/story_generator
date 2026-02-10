# Re:Zero End-to-End Lessons Learned

This write-up captures the practical issues observed while running a full
Re:Zero chapter pipeline and the improvements baked into the current tooling.

## What went wrong

- Rate limiting and throttling from remote translation services caused retries,
  empty output, and long end-to-end execution times.
- Some translation responses returned empty strings or output dominated by
  placeholder characters.
- Long chapters exceeded single-request size limits.
- A lack of per-chapter timing made it hard to compare runs apples-to-apples.

## What we changed

- Added a batch pipeline runner with per-chapter summaries and timing totals.
- Added translation retry + backoff handling for 429/503 responses.
- Added an offline translation option (`argostranslate`) that avoids external
  rate limits when installed.
- Added output summaries for pipeline duration and per-stage timing to improve
  comparability across runs.

## Reliability guidance

- Prefer offline translation when possible for large batch runs.
- Use chunked translation and apply delay between requests to keep APIs stable.
- Track `summary.json` timing totals after each run and compare against prior
  runs using the same chapter set.

## Next improvements

- Add translation quality scoring to highlight low-confidence chapters.
- Improve retry logic to include circuit breaking when throttling is sustained.
- Add regression baselines for large story sets under `work/pipeline_runs/`.
