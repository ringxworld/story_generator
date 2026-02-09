# Interactive Graph Strategy

This project currently ships deterministic SVG/PNG graph exports plus a React-rendered
interactive node-link view. The goal is to keep deep insight available without
locking into heavyweight infrastructure too early.

## Visualization options evaluated

- `D3`:
  - strengths: high control, mature ecosystem, great for 2D analytical graphs
  - tradeoffs: more custom code and layout ownership
- `Three.js`:
  - strengths: strong for 3D/high-density scenes and visual storytelling
  - tradeoffs: more rendering complexity and higher performance tuning burden
- `Cytoscape.js`:
  - strengths: graph-native interactions/layouts out of the box
  - tradeoffs: less bespoke visual language unless heavily themed

Current recommendation:

- keep the current React/SVG approach for alpha
- preserve deterministic `layout_x/layout_y` from backend so frontend renderer
  can evolve (D3 or Cytoscape) without changing extraction contracts

## Storage options evaluated

- SQLite/JSON (current):
  - strengths: simple local-first persistence, low ops, easy backup
  - tradeoffs: limited native graph traversal ergonomics
- MongoDB:
  - strengths: document-friendly for pipeline artifacts and nested JSON outputs
  - tradeoffs: graph traversal still application-managed
- Graph DB (Neo4j/Memgraph):
  - strengths: first-class relationship queries and graph analytics
  - tradeoffs: additional infra/ops complexity and migration overhead

Current recommendation:

- keep SQLite for alpha and deterministic contract validation
- introduce a graph-store adapter only when query workload proves it is needed
