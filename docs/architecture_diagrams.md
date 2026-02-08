# Architecture Diagrams

This page keeps the big picture visual so the repository remains navigable even
as features grow.

## 1. System context

```mermaid
flowchart LR
    Writer[Writer / Analyst]
    Web[React TS Studio]
    Py[Python CLI + API Client]
    API[FastAPI Service]
    Core[Core Feature Pipeline]
    DB[(SQLite / Postgres)]
    Obj[(MinIO / S3 Compatible Storage)]
    Pages[GitHub Pages]

    Writer --> Web
    Writer --> Py
    Web --> API
    Py --> API
    API --> Core
    API --> DB
    API --> Obj
    Pages --> Writer
```

## 2. Internal backend component map

```mermaid
flowchart TB
    subgraph API_Layer[src/story_gen/api]
      App[app.py]
      Contracts[contracts.py]
      PyIf[python_interface.py]
    end

    subgraph Core_Layer[src/story_gen/core]
      SFP[story_feature_pipeline.py]
    end

    subgraph Adapter_Layer[src/story_gen/adapters]
      StoryStore[sqlite_story_store.py]
      FeatureStore[sqlite_feature_store.py]
    end

    subgraph CLI_Layer[src/story_gen/cli]
      CLIFeatures[features.py]
      CLIBlueprint[blueprint.py]
      CLIOther[other command entrypoints]
    end

    App --> Contracts
    App --> StoryStore
    App --> FeatureStore
    App --> SFP
    PyIf --> Contracts
    CLIFeatures --> StoryStore
    CLIFeatures --> FeatureStore
    CLIFeatures --> SFP
    CLIBlueprint --> Contracts
```

## 3. Story-first feature extraction flow

```mermaid
sequenceDiagram
    participant U as User
    participant W as Web/Python Client
    participant A as FastAPI
    participant S as Story Store
    participant C as Core Pipeline
    participant F as Feature Store

    U->>W: Request feature extraction
    W->>A: POST /stories/{id}/features/extract
    A->>S: Load owner-scoped story blueprint
    S-->>A: Story + chapters
    A->>C: extract_story_features(chapters)
    C-->>A: StoryFeatureExtractionResult(v1)
    A->>F: Persist run + chapter feature rows
    F-->>A: run_id
    A-->>W: StoryFeatureRunResponse
```

## 4. BPMN-style workflow (lanes)

```mermaid
flowchart LR
    subgraph Product[Product Lane]
      P1([Define Story Goals])
      P2([Create/Update Blueprint])
      P3([Review Feature Output])
    end

    subgraph Platform[Platform Lane]
      E1([Validate Pydantic Contracts])
      E2([Persist Story Schema])
      E3([Extract Chapter Features])
      E4([Persist Feature Run v1])
      E5([Serve API + Python Interface])
    end

    subgraph Quality[Quality Lane]
      Q1([Run Tests + Type Checks])
      Q2([Enforce CI Gates])
      Q3([Update Docs/ADR if Needed])
    end

    P1 --> P2 --> E1 --> E2 --> E3 --> E4 --> E5 --> P3
    E3 --> Q1 --> Q2 --> Q3 --> P3
```

## 5. Deployment topology (planned)

```mermaid
flowchart TB
    Internet[Internet]
    Pages[GitHub Pages<br/>Docs + Static Web]
    Droplet[DigitalOcean Droplet]
    Proxy[Caddy/Nginx]
    FastAPI[FastAPI Container]
    Postgres[(Postgres)]
    Minio[(MinIO / Spaces)]

    Internet --> Pages
    Internet --> Proxy
    Droplet --> Proxy
    Proxy --> FastAPI
    FastAPI --> Postgres
    FastAPI --> Minio
```
