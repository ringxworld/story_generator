import { useMemo, useState } from "react";

import type {
  DashboardArcPointResponse,
  DashboardGraphResponse,
  DashboardOverviewResponse,
  DashboardThemeHeatmapCellResponse,
  DashboardTimelineLaneResponse,
} from "./types";

const overview: DashboardOverviewResponse = {
  title: "Story Intelligence Overview",
  macro_thesis:
    "A forged archive triggers civic conflict, but evidence and witness memory restore shared truth.",
  confidence_floor: 0.74,
  quality_passed: true,
  events_count: 7,
  beats_count: 7,
  themes_count: 4,
};

const timeline: DashboardTimelineLaneResponse[] = [
  {
    lane: "narrative_order",
    items: [
      { id: "p1", label: "Rhea finds ledger fragments.", order: 1, time: null },
      { id: "p2", label: "Council rejects authenticity claim.", order: 2, time: null },
      { id: "p3", label: "Street unrest spreads.", order: 3, time: null },
      { id: "p4", label: "Public hearing reveals cross-archive mismatch.", order: 4, time: null },
      { id: "p5", label: "Confession from records keeper.", order: 5, time: null },
      { id: "p6", label: "Emergency reform vote passes.", order: 6, time: null },
      { id: "p7", label: "City memorial updates canon.", order: 7, time: null },
    ],
  },
  {
    lane: "actual_time",
    items: [
      { id: "a1", label: "First archive audit", order: 1, time: "2025-04-03T09:00:00Z" },
      { id: "a2", label: "Council session", order: 2, time: "2025-04-05T18:00:00Z" },
      { id: "a3", label: "Public hearing", order: 3, time: "2025-04-08T14:00:00Z" },
      { id: "a4", label: "Reform vote", order: 4, time: "2025-04-09T20:30:00Z" },
    ],
  },
];

const heatmap: DashboardThemeHeatmapCellResponse[] = [
  { theme: "memory", stage: "setup", intensity: 0.5 },
  { theme: "memory", stage: "climax", intensity: 0.92 },
  { theme: "trust", stage: "escalation", intensity: 0.72 },
  { theme: "trust", stage: "resolution", intensity: 0.81 },
  { theme: "conflict", stage: "escalation", intensity: 0.95 },
  { theme: "identity", stage: "setup", intensity: 0.63 },
];

const arcs: DashboardArcPointResponse[] = [
  { lane: "character:rhea", stage: "setup", value: 0.4, label: "uncertain" },
  { lane: "character:rhea", stage: "climax", value: 0.88, label: "assertive" },
  { lane: "conflict", stage: "escalation", value: 0.94, label: "public fracture" },
  { lane: "conflict", stage: "resolution", value: 0.21, label: "institutional repair" },
  { lane: "emotion", stage: "setup", value: 0.36, label: "tense" },
  { lane: "emotion", stage: "resolution", value: 0.79, label: "hopeful" },
];

const graph: DashboardGraphResponse = {
  nodes: [
    { id: "theme_memory", label: "memory", group: "theme", stage: "climax" },
    { id: "theme_trust", label: "trust", group: "theme", stage: "resolution" },
    { id: "theme_conflict", label: "conflict", group: "theme", stage: "escalation" },
    { id: "beat_1", label: "B1", group: "beat", stage: "setup" },
    { id: "beat_2", label: "B2", group: "beat", stage: "escalation" },
    { id: "beat_3", label: "B3", group: "beat", stage: "climax" },
    { id: "beat_4", label: "B4", group: "beat", stage: "resolution" },
    { id: "arc_rhea", label: "rhea", group: "character", stage: "climax" },
  ],
  edges: [
    { source: "theme_memory", target: "beat_1", relation: "seeded_in", weight: 0.56 },
    { source: "theme_conflict", target: "beat_2", relation: "expressed_in", weight: 0.91 },
    { source: "theme_memory", target: "beat_3", relation: "proven_in", weight: 0.98 },
    { source: "theme_trust", target: "beat_4", relation: "resolved_in", weight: 0.83 },
    { source: "arc_rhea", target: "beat_3", relation: "drives", weight: 0.88 },
  ],
};

const formatLane = (lane: string): string => {
  const spaced = lane.replace(/_/g, " ");
  return `${spaced.charAt(0).toUpperCase()}${spaced.slice(1)}`;
};

export const OfflineDemoStudio = (): JSX.Element => {
  const brandMarkUrl = `${import.meta.env.BASE_URL}brand/story-gen-mark.svg`;
  const [selectedNodeId, setSelectedNodeId] = useState<string>(graph.nodes[0]?.id ?? "");
  const selectedNode = useMemo(
    () => graph.nodes.find((node) => node.id === selectedNodeId) ?? graph.nodes[0] ?? null,
    [selectedNodeId],
  );

  return (
    <main className="shell">
      <header className="hero">
        <div className="hero-head">
          <img
            className="brand-mark"
            src={brandMarkUrl}
            width={56}
            height={56}
            alt="story_gen brand mark"
          />
          <div>
            <h1>story_gen studio</h1>
            <p>Offline demo mode for GitHub Pages. No backend required.</p>
            <p className="hero-note">
              This view shows representative data from the story intelligence pipeline.
            </p>
          </div>
        </div>
      </header>

      <section className="card">
        <h2>Offline Demo Mode</h2>
        <div className="pill-row">
          <span className="pill">Macro, meso, micro insights</span>
          <span className="pill">Timeline and themes</span>
          <span className="pill">Interactive graph</span>
        </div>
      </section>

      <section className="card">
        <h2>{overview.title}</h2>
        <p className="status">{overview.macro_thesis}</p>
        <div className="kpi-grid">
          <article className="kpi-card">
            <strong>Confidence floor</strong>
            <div>{overview.confidence_floor.toFixed(2)}</div>
          </article>
          <article className="kpi-card">
            <strong>Quality gate</strong>
            <div>{overview.quality_passed ? "pass" : "warn"}</div>
          </article>
          <article className="kpi-card">
            <strong>Events / Beats</strong>
            <div>
              {overview.events_count} / {overview.beats_count}
            </div>
          </article>
          <article className="kpi-card">
            <strong>Themes</strong>
            <div>{overview.themes_count}</div>
          </article>
        </div>
      </section>

      <section className="card demo-board">
        <article>
          <h3>Timeline Lanes</h3>
          {timeline.map((lane) => (
            <div key={lane.lane}>
              <strong>{formatLane(lane.lane)}</strong>
              <ol className="timeline-list">
                {lane.items.slice(0, 6).map((item) => (
                  <li key={String(item.id)}>
                    {String(item.label)} {item.time ? `(${String(item.time)})` : ""}
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </article>
        <article>
          <h3>Theme Heatmap (sample)</h3>
          <table className="theme-table">
            <thead>
              <tr>
                <th>Theme</th>
                <th>Stage</th>
                <th>Intensity</th>
              </tr>
            </thead>
            <tbody>
              {heatmap.map((cell) => (
                <tr key={`${cell.theme}-${cell.stage}`}>
                  <td>{cell.theme}</td>
                  <td>{cell.stage}</td>
                  <td>{cell.intensity.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>

      <section className="card demo-board">
        <article>
          <h3>Arc Signals</h3>
          <ul>
            {arcs.map((point) => (
              <li key={`${point.lane}-${point.stage}`}>
                {point.lane} | {point.stage} | {point.label} ({point.value.toFixed(2)})
              </li>
            ))}
          </ul>
        </article>
        <article>
          <h3>Interactive Graph</h3>
          <svg className="graph-wrap" viewBox="0 0 560 220" role="img" aria-label="offline-demo-graph">
            {graph.edges.map((edge, index) => {
              const sourceIndex = graph.nodes.findIndex((node) => node.id === edge.source);
              const targetIndex = graph.nodes.findIndex((node) => node.id === edge.target);
              const x1 = 40 + (sourceIndex % 4) * 130;
              const y1 = 35 + Math.floor(sourceIndex / 4) * 90;
              const x2 = 40 + (targetIndex % 4) * 130;
              const y2 = 35 + Math.floor(targetIndex / 4) * 90;
              return (
                <line key={`${edge.source}-${edge.target}-${index}`} x1={x1} y1={y1} x2={x2} y2={y2} />
              );
            })}
            {graph.nodes.map((node, index) => {
              const x = 40 + (index % 4) * 130;
              const y = 35 + Math.floor(index / 4) * 90;
              const selected = selectedNode?.id === node.id;
              return (
                <g key={node.id}>
                  <circle
                    cx={x}
                    cy={y}
                    r={selected ? 11 : 8}
                    onClick={() => setSelectedNodeId(node.id)}
                    aria-label={`node-${node.label}`}
                  />
                  <text x={x + 12} y={y + 4}>
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>
          {selectedNode ? (
            <div className="status">
              Selected: {selectedNode.label} | group: {selectedNode.group}
              {selectedNode.stage ? ` | stage: ${selectedNode.stage}` : ""}
            </div>
          ) : null}
        </article>
      </section>
    </main>
  );
};
