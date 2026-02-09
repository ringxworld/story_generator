import { useMemo, useState, type KeyboardEvent, type ReactElement } from "react";

import type {
  DashboardArcPointResponse,
  DashboardDrilldownResponse,
  DashboardGraphResponse,
  DashboardOverviewResponse,
  DashboardThemeHeatmapCellResponse,
  DashboardTimelineLaneResponse,
} from "./types";
import { useThemeMode } from "./theme";

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
    { id: "theme_memory", label: "memory", group: "theme", stage: "climax", layout_x: 280, layout_y: 44 },
    { id: "theme_trust", label: "trust", group: "theme", stage: "resolution", layout_x: 430, layout_y: 44 },
    {
      id: "theme_conflict",
      label: "conflict",
      group: "theme",
      stage: "escalation",
      layout_x: 150,
      layout_y: 44,
    },
    { id: "beat_1", label: "B1", group: "beat", stage: "setup", layout_x: 60, layout_y: 112 },
    { id: "beat_2", label: "B2", group: "beat", stage: "escalation", layout_x: 175, layout_y: 112 },
    { id: "beat_3", label: "B3", group: "beat", stage: "climax", layout_x: 290, layout_y: 112 },
    { id: "beat_4", label: "B4", group: "beat", stage: "resolution", layout_x: 430, layout_y: 112 },
    { id: "arc_rhea_climax", label: "rhea", group: "character", stage: "climax", layout_x: 290, layout_y: 188 },
  ],
  edges: [
    { source: "theme_memory", target: "beat_1", relation: "seeded_in", weight: 0.56 },
    { source: "theme_conflict", target: "beat_2", relation: "expressed_in", weight: 0.91 },
    { source: "theme_memory", target: "beat_3", relation: "proven_in", weight: 0.98 },
    { source: "theme_trust", target: "beat_4", relation: "resolved_in", weight: 0.83 },
    { source: "arc_rhea_climax", target: "beat_3", relation: "drives", weight: 0.88 },
  ],
};

const drilldownById: Record<string, DashboardDrilldownResponse> = {
  "theme:theme_memory": {
    item_id: "theme:theme_memory",
    item_type: "theme",
    title: "Theme: memory (climax)",
    content: "Archival evidence peaks in the hearing sequence.",
    evidence_segment_ids: ["seg_03", "seg_04"],
  },
  "arc:rhea:climax": {
    item_id: "arc:rhea:climax",
    item_type: "arc",
    title: "Character Arc: rhea (climax)",
    content: "Rhea moves from doubt to assertive testimony under pressure.",
    evidence_segment_ids: ["seg_04", "seg_05"],
  },
};

type StoryStage = "setup" | "escalation" | "climax" | "resolution";
type NodeGroupFilter = "all" | "theme" | "beat" | "character";
type ExportView = "graph" | "timeline" | "theme-heatmap";
type ExportFormat = "svg" | "png";

const formatLane = (lane: string): string => {
  const spaced = lane.replace(/_/g, " ");
  return `${spaced.charAt(0).toUpperCase()}${spaced.slice(1)}`;
};

export const OfflineDemoStudio = (): ReactElement => {
  const brandMarkUrl = `${import.meta.env.BASE_URL}brand/story-gen-mark.svg`;
  const { theme, toggleTheme } = useThemeMode();
  const [selectedNodeId, setSelectedNodeId] = useState<string>(graph.nodes[0]?.id ?? "");
  const [stageFilter, setStageFilter] = useState<StoryStage | "all">("all");
  const [groupFilter, setGroupFilter] = useState<NodeGroupFilter>("all");
  const [themeFilter, setThemeFilter] = useState("all");
  const [entityFilter, setEntityFilter] = useState("all");
  const [relationFilter, setRelationFilter] = useState("all");
  const [labelFilter, setLabelFilter] = useState("");
  const [exportView, setExportView] = useState<ExportView>("graph");
  const [exportFormat, setExportFormat] = useState<ExportFormat>("svg");
  const [exportPayload, setExportPayload] = useState("");
  const [exportHref, setExportHref] = useState("");
  const [exportFilename, setExportFilename] = useState("");

  const themeOptions = useMemo(
    () =>
      Array.from(new Set(graph.nodes.filter((node) => node.group === "theme").map((node) => node.label))).sort(
        (a, b) => a.localeCompare(b),
      ),
    [],
  );
  const entityOptions = useMemo(
    () =>
      Array.from(
        new Set(graph.nodes.filter((node) => node.group === "character").map((node) => node.label)),
      ).sort((a, b) => a.localeCompare(b)),
    [],
  );
  const relationOptions = useMemo(
    () => Array.from(new Set(graph.edges.map((edge) => edge.relation))).sort((a, b) => a.localeCompare(b)),
    [],
  );

  const filteredGraph = useMemo((): DashboardGraphResponse => {
    const normalizedLabel = labelFilter.trim().toLowerCase();
    let visibleNodes = graph.nodes.filter((node) => {
      if (stageFilter !== "all" && node.stage !== stageFilter) {
        return false;
      }
      if (groupFilter !== "all" && node.group !== groupFilter) {
        return false;
      }
      if (normalizedLabel && !node.label.toLowerCase().includes(normalizedLabel)) {
        return false;
      }
      return true;
    });

    const expandConnected = (seedIds: Set<string>): Set<string> => {
      const expanded = new Set(seedIds);
      let changed = true;
      while (changed) {
        changed = false;
        for (const edge of graph.edges) {
          if (expanded.has(edge.source) || expanded.has(edge.target)) {
            if (!expanded.has(edge.source)) {
              expanded.add(edge.source);
              changed = true;
            }
            if (!expanded.has(edge.target)) {
              expanded.add(edge.target);
              changed = true;
            }
          }
        }
      }
      return expanded;
    };

    if (themeFilter !== "all") {
      const seed = new Set(
        graph.nodes.filter((node) => node.group === "theme" && node.label === themeFilter).map((node) => node.id),
      );
      const allowed = expandConnected(seed);
      visibleNodes = visibleNodes.filter((node) => allowed.has(node.id));
    }
    if (entityFilter !== "all") {
      const seed = new Set(
        graph.nodes
          .filter((node) => node.group === "character" && node.label === entityFilter)
          .map((node) => node.id),
      );
      const allowed = expandConnected(seed);
      visibleNodes = visibleNodes.filter((node) => allowed.has(node.id));
    }

    const visibleIds = new Set(visibleNodes.map((node) => node.id));
    const visibleEdges = graph.edges.filter((edge) => {
      if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) {
        return false;
      }
      if (relationFilter !== "all" && edge.relation !== relationFilter) {
        return false;
      }
      return true;
    });
    return { nodes: visibleNodes, edges: visibleEdges };
  }, [stageFilter, groupFilter, labelFilter, themeFilter, entityFilter, relationFilter]);

  const selectedNode = useMemo(
    () => filteredGraph.nodes.find((node) => node.id === selectedNodeId) ?? filteredGraph.nodes[0] ?? null,
    [filteredGraph, selectedNodeId],
  );
  const graphNodePositionById = useMemo(
    () =>
      new Map(
        filteredGraph.nodes.map((node, index) => [
          node.id,
          {
            x: typeof node.layout_x === "number" ? node.layout_x : 40 + (index % 4) * 130,
            y: typeof node.layout_y === "number" ? node.layout_y : 35 + Math.floor(index / 4) * 90,
          },
        ]),
      ),
    [filteredGraph],
  );

  const activeStage = selectedNode?.stage ?? (stageFilter === "all" ? null : stageFilter);
  const activeTheme = selectedNode?.group === "theme" ? selectedNode.label.toLowerCase() : null;
  const activeEntity = selectedNode?.group === "character" ? selectedNode.label.toLowerCase() : null;

  const relatedBeatOrders = useMemo(() => {
    const result = new Set<number>();
    if (!selectedNode) {
      return result;
    }
    for (const edge of graph.edges) {
      const candidateId =
        edge.source === selectedNode.id ? edge.target : edge.target === selectedNode.id ? edge.source : null;
      if (!candidateId) {
        continue;
      }
      const beat = graph.nodes.find((node) => node.id === candidateId && node.group === "beat");
      if (!beat) {
        continue;
      }
      const match = /^B(\d+)$/i.exec(beat.label);
      if (match) {
        result.add(Number(match[1]));
      }
    }
    return result;
  }, [selectedNode]);

  const drilldown = useMemo(() => {
    if (!selectedNode) {
      return null;
    }
    if (selectedNode.group === "theme") {
      return drilldownById[`theme:${selectedNode.id}`] ?? null;
    }
    if (selectedNode.group === "character") {
      const match = /^arc_(.+)_(setup|escalation|climax|resolution)$/.exec(selectedNode.id);
      if (match) {
        return drilldownById[`arc:${match[1]}:${match[2]}`] ?? null;
      }
    }
    return null;
  }, [selectedNode]);

  const onGraphKeyDown = (event: KeyboardEvent<SVGSVGElement>): void => {
    if (!filteredGraph.nodes.length) {
      return;
    }
    const currentIndex = Math.max(
      0,
      filteredGraph.nodes.findIndex((node) => node.id === selectedNode?.id),
    );
    const setIndex = (nextIndex: number): void => {
      const wrapped = (nextIndex + filteredGraph.nodes.length) % filteredGraph.nodes.length;
      setSelectedNodeId(filteredGraph.nodes[wrapped].id);
    };
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      setIndex(currentIndex + 1);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      setIndex(currentIndex - 1);
    }
  };

  const onGenerateExportPreset = (): void => {
    if (exportFormat === "svg") {
      const svg = `<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 240 40\"><text x=\"8\" y=\"24\">offline-${exportView}</text></svg>`;
      const href = `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
      setExportPayload(svg);
      setExportHref(href);
      setExportFilename(`offline-${exportView}.svg`);
      return;
    }
    const payload = btoa(`offline:${exportView}:png`);
    const href = `data:image/png;base64,${payload}`;
    setExportPayload(`PNG bytes (base64 length): ${payload.length}`);
    setExportHref(href);
    setExportFilename(`offline-${exportView}.png`);
  };

  return (
    <main className="shell">
      <header className="hero">
        <div className="hero-head">
          <div className="hero-main">
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
          <button type="button" className="muted theme-toggle" onClick={toggleTheme}>
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
        </div>
      </header>

      <section className="card">
        <h2>Offline Demo Mode</h2>
        <div className="pill-row">
          <span className="pill">Macro, meso, micro insights</span>
          <span className="pill">Timeline and themes</span>
          <span className="pill">Interactive graph</span>
          <span className="pill">Export presets</span>
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
                {lane.items.slice(0, 6).map((item) => {
                  const order = typeof item.order === "number" ? item.order : NaN;
                  const highlighted = Number.isFinite(order) && relatedBeatOrders.has(order);
                  return (
                    <li key={String(item.id)} className={highlighted ? "highlight-chip" : ""}>
                      {String(item.label)} {item.time ? `(${String(item.time)})` : ""}
                    </li>
                  );
                })}
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
              {heatmap.map((cell) => {
                const highlightByTheme = !!activeTheme && cell.theme.toLowerCase() === activeTheme;
                const highlightByStage = !!activeStage && cell.stage === activeStage;
                return (
                  <tr
                    key={`${cell.theme}-${cell.stage}`}
                    className={highlightByTheme || highlightByStage ? "highlight-chip" : ""}
                  >
                    <td>{cell.theme}</td>
                    <td>{cell.stage}</td>
                    <td>{cell.intensity.toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </article>
      </section>

      <section className="card demo-board">
        <article>
          <h3>Arc Signals</h3>
          <ul>
            {arcs.map((point) => {
              const highlightByEntity = !!activeEntity && point.lane.toLowerCase().includes(activeEntity);
              const highlightByStage = !!activeStage && point.stage === activeStage;
              return (
                <li
                  key={`${point.lane}-${point.stage}`}
                  className={highlightByEntity || highlightByStage ? "highlight-chip" : ""}
                >
                  {point.lane} | {point.stage} | {point.label} ({point.value.toFixed(2)})
                </li>
              );
            })}
          </ul>
        </article>
        <article>
          <h3>Interactive Graph</h3>
          <div className="filter-grid">
            <label>
              Stage
              <select value={stageFilter} onChange={(event) => setStageFilter(event.target.value as StoryStage | "all")}>
                <option value="all">all</option>
                <option value="setup">setup</option>
                <option value="escalation">escalation</option>
                <option value="climax">climax</option>
                <option value="resolution">resolution</option>
              </select>
            </label>
            <label>
              Group
              <select value={groupFilter} onChange={(event) => setGroupFilter(event.target.value as NodeGroupFilter)}>
                <option value="all">all</option>
                <option value="theme">theme</option>
                <option value="beat">beat</option>
                <option value="character">character</option>
              </select>
            </label>
            <label>
              Theme
              <select value={themeFilter} onChange={(event) => setThemeFilter(event.target.value)}>
                <option value="all">all</option>
                {themeOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Entity
              <select value={entityFilter} onChange={(event) => setEntityFilter(event.target.value)}>
                <option value="all">all</option>
                {entityOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Relation
              <select value={relationFilter} onChange={(event) => setRelationFilter(event.target.value)}>
                <option value="all">all</option>
                {relationOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Label filter
              <input value={labelFilter} onChange={(event) => setLabelFilter(event.target.value)} />
            </label>
          </div>
          <svg
            className="graph-wrap"
            viewBox="0 0 560 260"
            role="img"
            aria-label="offline-demo-graph"
            tabIndex={0}
            onKeyDown={onGraphKeyDown}
          >
            <rect x="10" y="10" width="220" height="38" rx="8" fill="#2a251f" opacity="0.88" />
            <circle cx="24" cy="29" r="7" />
            <text x="36" y="32">theme / beat / character</text>
            <line x1="152" y1="29" x2="180" y2="29" />
            <text x="188" y="32">filtered relation</text>
            {filteredGraph.edges.map((edge, index) => {
              const source = graphNodePositionById.get(edge.source);
              const target = graphNodePositionById.get(edge.target);
              if (!source || !target) {
                return null;
              }
              const connected = edge.source === selectedNode?.id || edge.target === selectedNode?.id;
              return (
                <line
                  key={`${edge.source}-${edge.target}-${index}`}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={connected ? "#d6c28a" : undefined}
                  strokeWidth={connected ? 2.2 : undefined}
                />
              );
            })}
            {filteredGraph.nodes.map((node, index) => {
              const positioned = graphNodePositionById.get(node.id) ?? {
                x: 40 + (index % 4) * 130,
                y: 35 + Math.floor(index / 4) * 90,
              };
              const selected = selectedNode?.id === node.id;
              return (
                <g
                  key={node.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedNodeId(node.id)}
                  aria-label={`node-${node.label}`}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedNodeId(node.id);
                    }
                  }}
                >
                  <circle cx={positioned.x} cy={positioned.y} r={selected ? 11 : 8} />
                  <text x={positioned.x + 12} y={positioned.y + 4}>
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>
          <div className="status">
            Keyboard: arrow keys move node selection.
            {selectedNode
              ? ` Selected: ${selectedNode.label} (${selectedNode.group}${selectedNode.stage ? ` / ${selectedNode.stage}` : ""})`
              : " No nodes match current filters."}
          </div>
          <div className="status">
            <strong>Drilldown</strong>
            {drilldown ? (
              <>
                <div>
                  {drilldown.title} ({drilldown.item_type})
                </div>
                <div>{drilldown.content}</div>
                <div>Evidence: {drilldown.evidence_segment_ids.join(", ")}</div>
              </>
            ) : (
              <div>No drilldown panel for selected node.</div>
            )}
          </div>
          <div className="filter-grid">
            <label>
              Export view
              <select value={exportView} onChange={(event) => setExportView(event.target.value as ExportView)}>
                <option value="graph">graph</option>
                <option value="timeline">timeline</option>
                <option value="theme-heatmap">theme-heatmap</option>
              </select>
            </label>
            <label>
              Export format
              <select value={exportFormat} onChange={(event) => setExportFormat(event.target.value as ExportFormat)}>
                <option value="svg">svg</option>
                <option value="png">png</option>
              </select>
            </label>
            <div className="inline-actions">
              <button type="button" className="muted" onClick={onGenerateExportPreset}>
                Generate Export Preset
              </button>
              {exportHref ? (
                <a className="export-link" href={exportHref} download={exportFilename}>
                  Download {exportFilename}
                </a>
              ) : null}
            </div>
          </div>
          {exportPayload ? (
            <details>
              <summary>Export payload preview</summary>
              <textarea readOnly rows={6} value={exportPayload} />
            </details>
          ) : null}
        </article>
      </section>
    </main>
  );
};
