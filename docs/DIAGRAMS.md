# Diagrams — RLM-Lens

This folder provides diagrams in two forms:
- Mermaid sources (easy to edit)
- Exported SVGs in `assets/diagrams/` (easy to embed in README)

## 1. System architecture
Mermaid:
```mermaid
flowchart LR
  UI[Frontend] <-- REST/WS --> API[FastAPI]
  API --> IDX[Indexing]
  API --> DB[(SQLite)]
  API --> RLMRT[RLM runtime]
  RLMRT --> RLM[rlms]
  RLMRT --> TRACE[Trace JSONL + DB]
  IDX --> DB
```

Exported SVG:
- `assets/diagrams/architecture.svg`

## 2. Run lifecycle
```mermaid
sequenceDiagram
  participant U as User
  participant UI as Frontend
  participant API as Backend
  participant R as RLM Runtime
  U->>UI: Ask question
  UI->>API: POST /api/runs
  API->>R: start run
  R-->>API: events (metadata/iterations/subcalls)
  API-->>UI: stream events (WS/SSE)
  R-->>API: final answer + citations
  API-->>UI: run.complete
  UI->>API: POST /export
  API-->>UI: zip path
```

## 3. Starter corpus materialization
```mermaid
sequenceDiagram
  participant U as User
  participant UI as Onboarding UI
  participant API as Backend API
  participant SC as Starter Corpus Service
  U->>UI: Pick starter pack
  UI->>API: POST /api/starter-corpora/{id}/materialize
  API->>SC: materialize(pack)
  SC-->>API: path + file stats
  API-->>UI: materialized payload
  UI->>API: POST /api/corpora + POST /api/index
```

## 4. Deployment split
```mermaid
flowchart LR
  Browser --> Vercel
  Vercel --> Railway
  Railway --> Volume[(Persistent Data)]
  Railway --> OpenAI
```
