# Dependency Charts

These charts define high-level dependencies before concrete implementations are added.

## 1) Concept Dependency Graph

```mermaid
graph TD
    Theme[Theme] --> Chapter[Chapter]
    Character[Character] --> Chapter
    Chapter --> StoryState[Story State]
    StoryBible[Story Bible] --> Theme
    StoryBible --> Character
    CanonRules[Canon Rules] --> StoryState
    StoryState --> DriftChecks[Drift Checks]
```

## 2) Implementation Layer Graph

```mermaid
graph LR
    CLI[CLI / Entrypoints] --> App[Application Services]
    App --> Domain[Domain Models + Ports]
    App --> Adapters[Adapters]
    Adapters --> LLM[LLM Provider]
    Adapters --> Storage[File/DB Repository]
    App --> Checks[Validation + Drift Checks]
    Checks --> Domain
```

## 3) Chapter Planning Flow

```mermaid
graph TD
    Bible[StoryBible] --> Planner[ChapterPlanner]
    Planner --> Outline[Chapter Outline]
    Outline --> DependencyValidation[Dependency Validation]
    DependencyValidation --> DraftGen[Draft Generation]
    DraftGen --> DriftCheck[Drift Check]
    DriftCheck --> Merge[Accept/Patch]
```

## Notes for concrete implementations

- Keep dependency direction inward: adapters depend on domain ports, not vice versa.
- Make drift checks pure where possible so they are testable and deterministic.
- Encode chapter prerequisites explicitly; avoid implicit sequence assumptions.
