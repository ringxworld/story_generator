# Agent Kickstart Pack

Use these files to bootstrap autonomous, quality-gated agent workflows in any repository.

## Files

- `SYSTEM_PROMPT.txt`
  - Copy/paste as your agent's system or developer prompt.
  - Encodes execution loop, quality gates, PR workflow, and close-out behavior.
- `AGENTS.md.template`
  - Drop into a target repo as `AGENTS.md`.
  - Acts as repository-local operating policy for any coding agent.

## Quick Start

1. Copy `templates/agent-kickstart/AGENTS.md.template` into the target repo as `AGENTS.md`.
2. Update placeholders:
   - `<OWNER>/<REPO>`
   - quality command list
   - optional language/tool-specific checks
3. Configure GitHub labels if missing:
   - `Priority: Critical`, `Priority: High`, `Priority: Medium`, `Priority: Low`
   - `Area: <domain>` labels (for example `Area: Dashboard`, `Area: NLP`)
4. Ensure the repo has:
   - `.github/pull_request_template.md`
   - `.github/ISSUE_CLOSE_SUMMARY_TEMPLATE.md`
   - CI workflow that runs quality gates
5. Use `SYSTEM_PROMPT.txt` as the runtime instruction block for your agent.

## Recommended Minimal CI Gates

- lockfile consistency check
- import/boundary check
- lint
- format check
- type check
- tests with coverage threshold
- docs build (strict)

## Notes

- Keep one source of truth for repo policy in `AGENTS.md`.
- Keep commands executable in both local runs and CI.
- Prefer failing fast on quality gates over post-merge cleanup.
