# Good Essay Mode

`good essay mode` is a separate product lane from story blueprints.

It exists to enforce coherence under long-context pressure by validating a
draft against explicit constraints instead of relying on free-form prompting.

## Core idea

An essay workspace has:

- `EssayBlueprint`: prompt + policy + rubric
- `draft_text`: current draft body
- deterministic evaluation output with explicit checks

## Expected essay interface

`EssayBlueprint` contains:

- `prompt`: assignment statement
- `policy`:
  - `thesis_statement`
  - `audience`
  - `tone`
  - `min_words` / `max_words`
  - `required_sections` (`key`, `purpose`, `min_paragraphs`, `required_terms`)
  - `banned_phrases`
  - `required_citations`
- `rubric`: optional quality criteria list

## API routes

- `GET /api/v1/essays`
- `POST /api/v1/essays`
- `GET /api/v1/essays/{essay_id}`
- `PUT /api/v1/essays/{essay_id}`
- `POST /api/v1/essays/{essay_id}/evaluate`

Evaluation returns:

- pass/fail
- score (0-100)
- word and citation counts
- structured checks (`error` / `warning`)

## JSON blueprint example

```json
{
  "prompt": "Argue for a constraint-first drafting workflow.",
  "policy": {
    "thesis_statement": "Constraint-first drafting improves coherence.",
    "audience": "technical readers",
    "tone": "analytical",
    "min_words": 300,
    "max_words": 900,
    "required_sections": [
      {
        "key": "introduction",
        "purpose": "Frame claim",
        "min_paragraphs": 1,
        "required_terms": ["coherence"]
      },
      {
        "key": "analysis",
        "purpose": "Defend claim",
        "min_paragraphs": 2,
        "required_terms": ["evidence"]
      },
      {
        "key": "conclusion",
        "purpose": "Synthesize claim",
        "min_paragraphs": 1,
        "required_terms": []
      }
    ],
    "banned_phrases": ["as an ai language model"],
    "required_citations": 1
  },
  "rubric": ["clear thesis", "evidence per claim", "logical flow"]
}
```
