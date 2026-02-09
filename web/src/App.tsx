import { FormEvent, useEffect, useMemo, useState, type KeyboardEvent, type ReactElement } from "react";

import {
  apiBaseUrl,
  createEssay,
  createStory,
  exportDashboardGraphPng,
  exportDashboardGraphSvg,
  exportDashboardThemeHeatmapPng,
  exportDashboardThemeHeatmapSvg,
  exportDashboardTimelinePng,
  exportDashboardTimelineSvg,
  evaluateEssay,
  getDashboardArcs,
  getDashboardDrilldown,
  getDashboardGraph,
  getDashboardOverview,
  getDashboardThemeHeatmap,
  getDashboardTimeline,
  getLatestStoryAnalysis,
  listEssays,
  listStories,
  login,
  me,
  register,
  runStoryAnalysis,
  updateEssay,
  updateStory,
} from "./api";
import { applyBlueprintToForm, buildBlueprintFromForm, emptyStoryForm, StoryFormState } from "./blueprint_form";
import { isOfflineDemoMode } from "./demo_mode";
import { OfflineDemoStudio } from "./offline_demo";
import { useThemeMode } from "./theme";
import type {
  DashboardArcPointResponse,
  DashboardDrilldownResponse,
  DashboardGraphNodeResponse,
  DashboardGraphResponse,
  DashboardOverviewResponse,
  DashboardThemeHeatmapCellResponse,
  DashboardTimelineLaneResponse,
  EssayBlueprint,
  EssayEvaluationResponse,
  EssayResponse,
  StoryAnalysisRunResponse,
  StoryResponse,
} from "./types";

const TOKEN_STORAGE_KEY = "story_gen.token";
const STORY_STAGES = ["setup", "escalation", "climax", "resolution"] as const;
type StoryStage = (typeof STORY_STAGES)[number];
type NodeGroupFilter = "all" | "theme" | "beat" | "character";
type ExportView = "graph" | "timeline" | "theme-heatmap";
type ExportFormat = "svg" | "png";

const graphNodeStage = (stage: string | null): StoryStage | null =>
  STORY_STAGES.includes(stage as StoryStage) ? (stage as StoryStage) : null;

const formatLane = (lane: string): string => {
  const spaced = lane.replace(/_/g, " ");
  return `${spaced.charAt(0).toUpperCase()}${spaced.slice(1)}`;
};

const defaultEssayBlueprint = (): EssayBlueprint => ({
  prompt: "Write an essay that argues a clear claim and defends it with evidence.",
  policy: {
    thesis_statement: "A defensible essay stays coherent by enforcing explicit constraints.",
    audience: "technical readers",
    tone: "analytical",
    min_words: 300,
    max_words: 900,
    required_sections: [
      { key: "introduction", purpose: "Frame thesis", min_paragraphs: 1, required_terms: [] },
      { key: "analysis", purpose: "Develop argument", min_paragraphs: 2, required_terms: [] },
      { key: "conclusion", purpose: "Synthesize claim", min_paragraphs: 1, required_terms: [] },
    ],
    banned_phrases: ["as an ai language model"],
    required_citations: 1,
  },
  rubric: ["clear thesis", "evidence per claim", "logical transitions"],
});

const App = (): ReactElement => {
  if (isOfflineDemoMode()) {
    return <OfflineDemoStudio />;
  }
  const brandMarkUrl = `${import.meta.env.BASE_URL}brand/story-gen-mark.svg`;
  const { theme, toggleTheme } = useThemeMode();

  const [token, setToken] = useState<string>(() => window.localStorage.getItem(TOKEN_STORAGE_KEY) ?? "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [status, setStatus] = useState("Ready.");

  const [stories, setStories] = useState<StoryResponse[]>([]);
  const [selectedStoryId, setSelectedStoryId] = useState<string | null>(null);
  const [storyForm, setStoryForm] = useState<StoryFormState>(emptyStoryForm);

  const [essays, setEssays] = useState<EssayResponse[]>([]);
  const [selectedEssayId, setSelectedEssayId] = useState<string | null>(null);
  const [essayTitle, setEssayTitle] = useState("");
  const [essayBlueprintRaw, setEssayBlueprintRaw] = useState(
    JSON.stringify(defaultEssayBlueprint(), null, 2),
  );
  const [essayDraftText, setEssayDraftText] = useState("");
  const [essayEvaluation, setEssayEvaluation] = useState<EssayEvaluationResponse | null>(null);
  const [analysisRun, setAnalysisRun] = useState<StoryAnalysisRunResponse | null>(null);
  const [dashboardOverview, setDashboardOverview] = useState<DashboardOverviewResponse | null>(null);
  const [dashboardTimeline, setDashboardTimeline] = useState<DashboardTimelineLaneResponse[]>([]);
  const [dashboardHeatmap, setDashboardHeatmap] = useState<DashboardThemeHeatmapCellResponse[]>([]);
  const [dashboardArcs, setDashboardArcs] = useState<DashboardArcPointResponse[]>([]);
  const [dashboardGraph, setDashboardGraph] = useState<DashboardGraphResponse | null>(null);
  const [graphSvg, setGraphSvg] = useState("");
  const [selectedGraphNodeId, setSelectedGraphNodeId] = useState<string | null>(null);
  const [drilldown, setDrilldown] = useState<DashboardDrilldownResponse | null>(null);
  const [drilldownStatus, setDrilldownStatus] = useState("Select a graph node to inspect details.");
  const [stageFilter, setStageFilter] = useState<StoryStage | "all">("all");
  const [groupFilter, setGroupFilter] = useState<NodeGroupFilter>("all");
  const [themeFilter, setThemeFilter] = useState("all");
  const [entityFilter, setEntityFilter] = useState("all");
  const [relationFilter, setRelationFilter] = useState("all");
  const [labelFilter, setLabelFilter] = useState("");
  const [exportView, setExportView] = useState<ExportView>("graph");
  const [exportFormat, setExportFormat] = useState<ExportFormat>("svg");
  const [exportPayloadPreview, setExportPayloadPreview] = useState("");
  const [exportHref, setExportHref] = useState("");
  const [exportFilename, setExportFilename] = useState("");

  const isAuthenticated = token.trim().length > 0;
  const selectedStory = useMemo(
    () => stories.find((story) => story.story_id === selectedStoryId) ?? null,
    [selectedStoryId, stories],
  );
  const selectedEssay = useMemo(
    () => essays.find((essay) => essay.essay_id === selectedEssayId) ?? null,
    [selectedEssayId, essays],
  );
  const themeOptions = useMemo(
    () =>
      Array.from(
        new Set(
          (dashboardGraph?.nodes ?? [])
            .filter((node) => node.group === "theme")
            .map((node) => node.label)
            .filter((label) => label.trim().length > 0),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [dashboardGraph],
  );
  const entityOptions = useMemo(
    () =>
      Array.from(
        new Set(
          (dashboardGraph?.nodes ?? [])
            .filter((node) => node.group === "character")
            .map((node) => node.label)
            .filter((label) => label.trim().length > 0),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [dashboardGraph],
  );
  const relationOptions = useMemo(
    () =>
      Array.from(
        new Set((dashboardGraph?.edges ?? []).map((edge) => edge.relation).filter((value) => value.trim().length > 0)),
      ).sort((a, b) => a.localeCompare(b)),
    [dashboardGraph],
  );

  const filteredGraph = useMemo((): DashboardGraphResponse | null => {
    if (!dashboardGraph) {
      return null;
    }
    const normalizedLabel = labelFilter.trim().toLowerCase();
    let visibleNodes = dashboardGraph.nodes.filter((node) => {
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
    const edges = dashboardGraph.edges;
    const expandConnected = (seedIds: Set<string>): Set<string> => {
      const expanded = new Set(seedIds);
      let changed = true;
      while (changed) {
        changed = false;
        for (const edge of edges) {
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
        dashboardGraph.nodes
          .filter((node) => node.group === "theme" && node.label === themeFilter)
          .map((node) => node.id),
      );
      const allowed = expandConnected(seed);
      visibleNodes = visibleNodes.filter((node) => allowed.has(node.id));
    }
    if (entityFilter !== "all") {
      const seed = new Set(
        dashboardGraph.nodes
          .filter((node) => node.group === "character" && node.label === entityFilter)
          .map((node) => node.id),
      );
      const allowed = expandConnected(seed);
      visibleNodes = visibleNodes.filter((node) => allowed.has(node.id));
    }
    const visibleIds = new Set(visibleNodes.map((node) => node.id));
    const visibleEdges = edges.filter((edge) => {
      if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) {
        return false;
      }
      if (relationFilter !== "all" && edge.relation !== relationFilter) {
        return false;
      }
      return true;
    });
    return {
      nodes: visibleNodes,
      edges: visibleEdges,
    };
  }, [dashboardGraph, stageFilter, groupFilter, labelFilter, themeFilter, entityFilter, relationFilter]);

  useEffect(() => {
    if (!filteredGraph?.nodes.length) {
      setSelectedGraphNodeId(null);
      return;
    }
    if (!selectedGraphNodeId || !filteredGraph.nodes.some((node) => node.id === selectedGraphNodeId)) {
      setSelectedGraphNodeId(filteredGraph.nodes[0].id);
    }
  }, [filteredGraph, selectedGraphNodeId]);

  const selectedGraphNode = useMemo(
    () =>
      filteredGraph?.nodes.find((node) => node.id === selectedGraphNodeId) ??
      (filteredGraph?.nodes[0] ?? null),
    [filteredGraph, selectedGraphNodeId],
  );
  const graphNodeIndexById = useMemo(
    () =>
      new Map(
        (filteredGraph?.nodes ?? []).map((node, index) => [
          node.id,
          {
            x:
              typeof node.layout_x === "number"
                ? node.layout_x
                : 30 + (index % 12) * 62,
            y:
              typeof node.layout_y === "number"
                ? node.layout_y
                : 30 + Math.floor(index / 12) * 60,
          },
        ]),
      ),
    [filteredGraph],
  );
  const activeStage = useMemo(() => {
    if (selectedGraphNode?.stage) {
      return graphNodeStage(selectedGraphNode.stage);
    }
    return stageFilter === "all" ? null : stageFilter;
  }, [selectedGraphNode, stageFilter]);
  const activeTheme = useMemo(() => {
    if (selectedGraphNode?.group === "theme") {
      return selectedGraphNode.label.toLowerCase();
    }
    return themeFilter === "all" ? null : themeFilter.toLowerCase();
  }, [selectedGraphNode, themeFilter]);
  const activeEntity = useMemo(() => {
    if (selectedGraphNode?.group === "character") {
      return selectedGraphNode.label.toLowerCase();
    }
    return entityFilter === "all" ? null : entityFilter.toLowerCase();
  }, [selectedGraphNode, entityFilter]);
  const relatedBeatOrders = useMemo(() => {
    const result = new Set<number>();
    if (!selectedGraphNode || !dashboardGraph) {
      return result;
    }
    const beatNodesById = new Map(
      dashboardGraph.nodes
        .filter((node) => node.group === "beat")
        .map((node) => {
          const match = /^B(\d+)$/i.exec(node.label);
          return [node.id, match ? Number(match[1]) : NaN];
        }),
    );
    const addOrderForNode = (node: DashboardGraphNodeResponse): void => {
      if (node.group !== "beat") {
        return;
      }
      const match = /^B(\d+)$/i.exec(node.label);
      if (match) {
        result.add(Number(match[1]));
      }
    };
    addOrderForNode(selectedGraphNode);
    for (const edge of dashboardGraph.edges) {
      if (edge.source === selectedGraphNode.id && beatNodesById.has(edge.target)) {
        const order = beatNodesById.get(edge.target) ?? NaN;
        if (Number.isFinite(order)) {
          result.add(order);
        }
      }
      if (edge.target === selectedGraphNode.id && beatNodesById.has(edge.source)) {
        const order = beatNodesById.get(edge.source) ?? NaN;
        if (Number.isFinite(order)) {
          result.add(order);
        }
      }
    }
    return result;
  }, [selectedGraphNode, dashboardGraph]);

  const refreshStories = async (currentToken: string): Promise<void> => {
    const freshStories = await listStories(currentToken);
    setStories(freshStories);
  };

  const refreshEssays = async (currentToken: string): Promise<void> => {
    const freshEssays = await listEssays(currentToken);
    setEssays(freshEssays);
  };

  const refreshStoryDashboard = async (currentToken: string, storyId: string): Promise<void> => {
    const [latest, overview, timeline, heatmap, arcs, graph, svgExport] = await Promise.all([
      getLatestStoryAnalysis(currentToken, storyId),
      getDashboardOverview(currentToken, storyId),
      getDashboardTimeline(currentToken, storyId),
      getDashboardThemeHeatmap(currentToken, storyId),
      getDashboardArcs(currentToken, storyId),
      getDashboardGraph(currentToken, storyId),
      exportDashboardGraphSvg(currentToken, storyId),
    ]);
    setAnalysisRun(latest);
    setDashboardOverview(overview);
    setDashboardTimeline(timeline);
    setDashboardHeatmap(heatmap);
    setDashboardArcs(arcs);
    setDashboardGraph(graph);
    setGraphSvg(svgExport.svg);
  };

  useEffect(() => {
    if (!selectedGraphNode || !selectedStory || !token.trim()) {
      setDrilldown(null);
      setDrilldownStatus("Select a graph node to inspect details.");
      return;
    }
    const candidates: string[] = [selectedGraphNode.id];
    if (selectedGraphNode.group === "theme") {
      candidates.unshift(`theme:${selectedGraphNode.id}`);
    }
    if (selectedGraphNode.group === "character") {
      const match = /^arc_(.+)_(setup|escalation|climax|resolution)$/.exec(selectedGraphNode.id);
      if (match) {
        candidates.unshift(`arc:${match[1]}:${match[2]}`);
      }
    }
    const uniqueCandidates = Array.from(new Set(candidates));
    let cancelled = false;
    setDrilldown(null);
    setDrilldownStatus("Loading drilldown details...");
    const run = async (): Promise<void> => {
      for (const candidate of uniqueCandidates) {
        try {
          const payload = await getDashboardDrilldown(token, selectedStory.story_id, candidate);
          if (cancelled) {
            return;
          }
          setDrilldown(payload);
          setDrilldownStatus(`Loaded drilldown: ${payload.item_type}`);
          return;
        } catch (error) {
          const message = (error as Error).message;
          if (message.includes("404")) {
            continue;
          }
          if (cancelled) {
            return;
          }
          setDrilldown(null);
          setDrilldownStatus(`Drilldown unavailable: ${message}`);
          return;
        }
      }
      if (!cancelled) {
        setDrilldown(null);
        setDrilldownStatus("No drilldown panel for the selected graph node.");
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [selectedGraphNode, selectedStory, token]);

  useEffect(
    () => () => {
      if (exportHref.startsWith("blob:")) {
        URL.revokeObjectURL(exportHref);
      }
    },
    [exportHref],
  );

  const resetExportHref = (): void => {
    if (exportHref.startsWith("blob:")) {
      URL.revokeObjectURL(exportHref);
    }
    setExportHref("");
    setExportFilename("");
  };

  const onRegister = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    try {
      await register(email, password, displayName || email);
      setStatus("Registered successfully. You can now log in.");
    } catch (error) {
      setStatus(`Registration failed: ${(error as Error).message}`);
    }
  };

  const onLogin = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    try {
      const auth = await login(email, password);
      window.localStorage.setItem(TOKEN_STORAGE_KEY, auth.access_token);
      setToken(auth.access_token);
      const user = await me(auth.access_token);
      await refreshStories(auth.access_token);
      await refreshEssays(auth.access_token);
      setStatus(`Signed in as ${user.display_name}.`);
    } catch (error) {
      setStatus(`Login failed: ${(error as Error).message}`);
    }
  };

  const onSignOut = (): void => {
    resetExportHref();
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken("");
    setStories([]);
    setEssays([]);
    setSelectedStoryId(null);
    setSelectedEssayId(null);
    setStoryForm(emptyStoryForm());
    setEssayTitle("");
    setEssayBlueprintRaw(JSON.stringify(defaultEssayBlueprint(), null, 2));
    setEssayDraftText("");
    setEssayEvaluation(null);
    setAnalysisRun(null);
    setDashboardOverview(null);
    setDashboardTimeline([]);
    setDashboardHeatmap([]);
    setDashboardArcs([]);
    setDashboardGraph(null);
    setGraphSvg("");
    setSelectedGraphNodeId(null);
    setDrilldown(null);
    setDrilldownStatus("Select a graph node to inspect details.");
    setExportPayloadPreview("");
    setStatus("Signed out.");
  };

  const onCreateOrUpdateStory = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!isAuthenticated) {
      setStatus("Sign in before saving stories.");
      return;
    }
    try {
      const blueprint = buildBlueprintFromForm(storyForm);
      if (selectedStory) {
        await updateStory(token, selectedStory.story_id, storyForm.title.trim(), blueprint);
        setStatus(`Updated story: ${storyForm.title}`);
      } else {
        const created = await createStory(token, storyForm.title.trim(), blueprint);
        setSelectedStoryId(created.story_id);
        setStatus(`Created story: ${created.title}`);
      }
      await refreshStories(token);
    } catch (error) {
      setStatus(`Save failed: ${(error as Error).message}`);
    }
  };

  const onCreateOrUpdateEssay = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!isAuthenticated) {
      setStatus("Sign in before saving essays.");
      return;
    }
    try {
      const blueprint = JSON.parse(essayBlueprintRaw) as EssayBlueprint;
      if (selectedEssay) {
        await updateEssay(token, selectedEssay.essay_id, essayTitle.trim(), blueprint, essayDraftText);
        setStatus(`Updated essay: ${essayTitle}`);
      } else {
        const created = await createEssay(token, essayTitle.trim(), blueprint, essayDraftText);
        setSelectedEssayId(created.essay_id);
        setStatus(`Created essay: ${created.title}`);
      }
      await refreshEssays(token);
    } catch (error) {
      setStatus(`Essay save failed: ${(error as Error).message}`);
    }
  };

  const onEvaluateEssay = async (): Promise<void> => {
    if (!isAuthenticated) {
      setStatus("Sign in before evaluating essays.");
      return;
    }
    if (!selectedEssay) {
      setStatus("Select an essay first.");
      return;
    }
    try {
      const evaluation = await evaluateEssay(token, selectedEssay.essay_id, essayDraftText);
      setEssayEvaluation(evaluation);
      setStatus(
        evaluation.passed
          ? `Essay passed checks with score ${evaluation.score.toFixed(1)}.`
          : `Essay failed checks with score ${evaluation.score.toFixed(1)}.`,
      );
    } catch (error) {
      setStatus(`Essay evaluation failed: ${(error as Error).message}`);
    }
  };

  const onRunStoryAnalysis = async (): Promise<void> => {
    if (!isAuthenticated) {
      setStatus("Sign in before running analysis.");
      return;
    }
    if (!selectedStory) {
      setStatus("Select a story first.");
      return;
    }
    try {
      const run = await runStoryAnalysis(token, selectedStory.story_id, {});
      setAnalysisRun(run);
      await refreshStoryDashboard(token, selectedStory.story_id);
      setSelectedGraphNodeId(null);
      setStatus(
        run.quality_gate.passed
          ? `Analysis complete (${run.event_count} events).`
          : `Analysis completed with warnings (${run.quality_gate.reasons.join(", ")}).`,
      );
    } catch (error) {
      setStatus(`Story analysis failed: ${(error as Error).message}`);
    }
  };

  const onSelectStory = (story: StoryResponse): void => {
    resetExportHref();
    setSelectedStoryId(story.story_id);
    setStoryForm(applyBlueprintToForm(story.title, story.blueprint));
    setAnalysisRun(null);
    setDashboardOverview(null);
    setDashboardTimeline([]);
    setDashboardHeatmap([]);
    setDashboardArcs([]);
    setDashboardGraph(null);
    setGraphSvg("");
    setSelectedGraphNodeId(null);
    setDrilldown(null);
    setDrilldownStatus("Select a graph node to inspect details.");
    setExportPayloadPreview("");
    setStageFilter("all");
    setGroupFilter("all");
    setThemeFilter("all");
    setEntityFilter("all");
    setRelationFilter("all");
    setLabelFilter("");
    if (token.trim()) {
      // Avoid clobbering foreground status updates from save/analyze actions.
      void refreshStoryDashboard(token, story.story_id).catch(() => undefined);
    }
  };

  const onSelectEssay = (essay: EssayResponse): void => {
    setSelectedEssayId(essay.essay_id);
    setEssayTitle(essay.title);
    setEssayDraftText(essay.draft_text);
    setEssayBlueprintRaw(JSON.stringify(essay.blueprint, null, 2));
    setEssayEvaluation(null);
  };

  const onGraphKeyDown = (event: KeyboardEvent<SVGSVGElement>): void => {
    if (!filteredGraph?.nodes.length) {
      return;
    }
    const currentIndex = Math.max(
      0,
      filteredGraph.nodes.findIndex((node) => node.id === selectedGraphNode?.id),
    );
    const setIndex = (nextIndex: number): void => {
      const wrapped = (nextIndex + filteredGraph.nodes.length) % filteredGraph.nodes.length;
      setSelectedGraphNodeId(filteredGraph.nodes[wrapped].id);
    };
    switch (event.key) {
      case "ArrowRight":
      case "ArrowDown":
        event.preventDefault();
        setIndex(currentIndex + 1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
        event.preventDefault();
        setIndex(currentIndex - 1);
        break;
      case "Home":
        event.preventDefault();
        setSelectedGraphNodeId(filteredGraph.nodes[0].id);
        break;
      case "End":
        event.preventDefault();
        setSelectedGraphNodeId(filteredGraph.nodes[filteredGraph.nodes.length - 1].id);
        break;
      default:
        break;
    }
  };

  const onGenerateExportPreset = async (): Promise<void> => {
    if (!token.trim() || !selectedStory) {
      setStatus("Select a story and sign in before generating exports.");
      return;
    }
    try {
      resetExportHref();
      if (exportView === "graph" && exportFormat === "svg") {
        const payload = await exportDashboardGraphSvg(token, selectedStory.story_id);
        const blob = new Blob([payload.svg], { type: "image/svg+xml;charset=utf-8" });
        setExportPayloadPreview(payload.svg.slice(0, 900));
        setExportHref(URL.createObjectURL(blob));
        setExportFilename(`${selectedStory.story_id}-graph.svg`);
      } else if (exportView === "graph" && exportFormat === "png") {
        const payload = await exportDashboardGraphPng(token, selectedStory.story_id);
        const url = `data:image/png;base64,${payload.png_base64}`;
        setExportPayloadPreview(`PNG bytes (base64 length): ${payload.png_base64.length}`);
        setExportHref(url);
        setExportFilename(`${selectedStory.story_id}-graph.png`);
      } else if (exportView === "timeline" && exportFormat === "svg") {
        const payload = await exportDashboardTimelineSvg(token, selectedStory.story_id);
        const blob = new Blob([payload.svg], { type: "image/svg+xml;charset=utf-8" });
        setExportPayloadPreview(payload.svg.slice(0, 900));
        setExportHref(URL.createObjectURL(blob));
        setExportFilename(`${selectedStory.story_id}-timeline.svg`);
      } else if (exportView === "timeline" && exportFormat === "png") {
        const payload = await exportDashboardTimelinePng(token, selectedStory.story_id);
        const url = `data:image/png;base64,${payload.png_base64}`;
        setExportPayloadPreview(`PNG bytes (base64 length): ${payload.png_base64.length}`);
        setExportHref(url);
        setExportFilename(`${selectedStory.story_id}-timeline.png`);
      } else if (exportView === "theme-heatmap" && exportFormat === "svg") {
        const payload = await exportDashboardThemeHeatmapSvg(token, selectedStory.story_id);
        const blob = new Blob([payload.svg], { type: "image/svg+xml;charset=utf-8" });
        setExportPayloadPreview(payload.svg.slice(0, 900));
        setExportHref(URL.createObjectURL(blob));
        setExportFilename(`${selectedStory.story_id}-theme-heatmap.svg`);
      } else {
        const payload = await exportDashboardThemeHeatmapPng(token, selectedStory.story_id);
        const url = `data:image/png;base64,${payload.png_base64}`;
        setExportPayloadPreview(`PNG bytes (base64 length): ${payload.png_base64.length}`);
        setExportHref(url);
        setExportFilename(`${selectedStory.story_id}-theme-heatmap.png`);
      }
      setStatus(`Generated ${exportView} ${exportFormat.toUpperCase()} export preset.`);
    } catch (error) {
      setStatus(`Export generation failed: ${(error as Error).message}`);
    }
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
              <p>
                Build strict contracts for story and essay generation workflows.
                API base: <code>{apiBaseUrl}</code>
              </p>
            </div>
          </div>
          <button type="button" className="muted theme-toggle" onClick={toggleTheme}>
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
        </div>
      </header>

      <section className="card">
        <h2>Auth</h2>
        <div className="grid">
          <form onSubmit={onRegister}>
            <h3>Register</h3>
            <label>
              Email
              <input value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <label>
              Password
              <input
                value={password}
                type="password"
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <label>
              Display name
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
            </label>
            <button type="submit">Register</button>
          </form>

          <form onSubmit={onLogin}>
            <h3>Sign In</h3>
            <label>
              Email
              <input value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <label>
              Password
              <input
                value={password}
                type="password"
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button type="submit">Sign In</button>
            <button type="button" className="muted" onClick={onSignOut}>
              Sign Out
            </button>
          </form>
        </div>
      </section>

      <section className="card">
        <h2>Story Blueprints</h2>
        <p className="status">{status}</p>
        <div className="grid story-grid">
          <aside>
            <h3>Saved stories</h3>
            <button
              type="button"
              className="muted"
              onClick={() => {
                resetExportHref();
                setSelectedStoryId(null);
                setStoryForm(emptyStoryForm());
                setAnalysisRun(null);
                setDashboardOverview(null);
                setDashboardTimeline([]);
                setDashboardHeatmap([]);
                setDashboardArcs([]);
                setDashboardGraph(null);
                setGraphSvg("");
                setSelectedGraphNodeId(null);
                setDrilldown(null);
                setDrilldownStatus("Select a graph node to inspect details.");
                setExportPayloadPreview("");
                setStageFilter("all");
                setGroupFilter("all");
                setThemeFilter("all");
                setEntityFilter("all");
                setRelationFilter("all");
                setLabelFilter("");
              }}
            >
              New story
            </button>
            <ul>
              {stories.map((story) => (
                <li key={story.story_id}>
                  <button type="button" onClick={() => onSelectStory(story)} className="link-button">
                    {story.title}
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          <form onSubmit={onCreateOrUpdateStory} className="stack">
            <label>
              Title
              <input
                value={storyForm.title}
                onChange={(event) => setStoryForm((state) => ({ ...state, title: event.target.value }))}
              />
            </label>
            <label>
              Premise
              <textarea
                rows={4}
                value={storyForm.premise}
                onChange={(event) => setStoryForm((state) => ({ ...state, premise: event.target.value }))}
              />
            </label>
            <label>
              Canon rules (one per line)
              <textarea
                rows={4}
                value={storyForm.canonRulesRaw}
                onChange={(event) => setStoryForm((state) => ({ ...state, canonRulesRaw: event.target.value }))}
              />
            </label>
            <label>
              Themes (`key|statement|priority`)
              <textarea
                rows={4}
                value={storyForm.themesRaw}
                onChange={(event) => setStoryForm((state) => ({ ...state, themesRaw: event.target.value }))}
              />
            </label>
            <label>
              Characters (`key|role|motivation`)
              <textarea
                rows={4}
                value={storyForm.charactersRaw}
                onChange={(event) => setStoryForm((state) => ({ ...state, charactersRaw: event.target.value }))}
              />
            </label>
            <label>
              Chapters (`key|title|objective|required_themes_csv|characters_csv|prerequisites_csv`)
              <textarea
                rows={5}
                value={storyForm.chaptersRaw}
                onChange={(event) => setStoryForm((state) => ({ ...state, chaptersRaw: event.target.value }))}
              />
            </label>
            <button type="submit">{selectedStory ? "Update Story" : "Create Story"}</button>
          </form>

          <article className="stack">
            <h3>Story Intelligence</h3>
            <div className="inline-actions">
              <button type="button" className="muted" onClick={() => void onRunStoryAnalysis()}>
                Run Analysis
              </button>
            </div>
            {analysisRun ? (
              <div className="status">
                <div>Run: {analysisRun.run_id}</div>
                <div>
                  Lang: {analysisRun.source_language} {"->"} {analysisRun.target_language}
                </div>
                <div>
                  Events: {analysisRun.event_count} | Beats: {analysisRun.beat_count} | Themes:{" "}
                  {analysisRun.theme_count}
                </div>
                <div>
                  Quality: {analysisRun.quality_gate.passed ? "pass" : "warn"} (confidence floor{" "}
                  {analysisRun.quality_gate.confidence_floor.toFixed(2)})
                </div>
              </div>
            ) : (
              <div className="status">Run analysis to generate timeline, themes, arcs, and graph.</div>
            )}
            {dashboardOverview ? (
              <div className="status">
                <strong>{dashboardOverview.title}</strong>
                <div>{dashboardOverview.macro_thesis}</div>
              </div>
            ) : null}
            <div className="status">
              <strong>Timeline lanes:</strong> {dashboardTimeline.length}
              <br />
              <strong>Heatmap cells:</strong> {dashboardHeatmap.length}
              <br />
              <strong>Arc points:</strong> {dashboardArcs.length}
            </div>
            {dashboardTimeline.map((lane) => (
              <div key={lane.lane}>
                <strong>{formatLane(lane.lane)}</strong>
                <ol className="timeline-list">
                  {lane.items.slice(0, 8).map((item) => {
                    const order = typeof item.order === "number" ? item.order : NaN;
                    const highlighted = Number.isFinite(order) && relatedBeatOrders.has(order);
                    return (
                      <li key={`${lane.lane}-${String(item.id)}`} className={highlighted ? "highlight-chip" : ""}>
                        {String(item.label)} {item.time ? `(${String(item.time)})` : ""}
                      </li>
                    );
                  })}
                </ol>
              </div>
            ))}
            {dashboardHeatmap.length ? (
              <table className="theme-table">
                <thead>
                  <tr>
                    <th>Theme</th>
                    <th>Stage</th>
                    <th>Intensity</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboardHeatmap.map((cell) => {
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
            ) : null}
            {dashboardArcs.length ? (
              <ul>
                {dashboardArcs.map((point) => {
                  const highlightByEntity = !!activeEntity && point.lane.toLowerCase().includes(activeEntity);
                  const highlightByStage = !!activeStage && point.stage === activeStage;
                  return (
                    <li
                      key={`${point.lane}-${point.stage}-${point.label}`}
                      className={highlightByEntity || highlightByStage ? "highlight-chip" : ""}
                    >
                      {point.lane} | {point.stage} | {point.label} ({point.value.toFixed(2)})
                    </li>
                  );
                })}
              </ul>
            ) : null}
            {filteredGraph ? (
              <div className="stack">
                <strong>Interactive Graph</strong>
                <div className="filter-grid">
                  <label>
                    Stage
                    <select
                      value={stageFilter}
                      onChange={(event) => setStageFilter(event.target.value as StoryStage | "all")}
                    >
                      <option value="all">all</option>
                      {STORY_STAGES.map((stage) => (
                        <option key={stage} value={stage}>
                          {stage}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Group
                    <select
                      value={groupFilter}
                      onChange={(event) => setGroupFilter(event.target.value as NodeGroupFilter)}
                    >
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
                    <input
                      value={labelFilter}
                      onChange={(event) => setLabelFilter(event.target.value)}
                      placeholder="theme/entity label"
                    />
                  </label>
                </div>
                <svg
                  className="graph-wrap"
                  viewBox="0 0 780 320"
                  role="img"
                  aria-label="story-graph"
                  tabIndex={0}
                  onKeyDown={onGraphKeyDown}
                >
                  <rect x="12" y="12" width="250" height="42" rx="8" fill="#2a251f" opacity="0.88" />
                  <circle cx="28" cy="32" r="7" fill="#4d8f7a" />
                  <text x="40" y="36">theme / beat / character</text>
                  <line x1="178" y1="32" x2="210" y2="32" stroke="#a7bcb2" strokeWidth="1.8" />
                  <text x="218" y="36">filtered relation</text>
                  {filteredGraph.edges.slice(0, 200).map((edge, index) => {
                    const source = graphNodeIndexById.get(edge.source);
                    const target = graphNodeIndexById.get(edge.target);
                    if (!source || !target) {
                      return null;
                    }
                    const connected =
                      edge.source === selectedGraphNode?.id || edge.target === selectedGraphNode?.id;
                    return (
                      <line
                        key={`${edge.source}-${edge.target}-${index}`}
                        x1={source.x}
                        y1={source.y}
                        x2={target.x}
                        y2={target.y}
                        stroke={connected ? "#d6c28a" : "#a7bcb2"}
                        strokeWidth={connected ? 2.2 : 1.1}
                      />
                    );
                  })}
                  {filteredGraph.nodes.slice(0, 200).map((node, index) => {
                    const positioned = graphNodeIndexById.get(node.id) ?? {
                      x: 30 + (index % 12) * 62,
                      y: 30 + Math.floor(index / 12) * 60,
                    };
                    const selected = node.id === selectedGraphNode?.id;
                    return (
                      <g
                        key={node.id}
                        role="button"
                        tabIndex={0}
                        aria-label={`node-${node.label}`}
                        onClick={() => setSelectedGraphNodeId(node.id)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            setSelectedGraphNodeId(node.id);
                          }
                        }}
                      >
                        <circle
                          cx={positioned.x}
                          cy={positioned.y}
                          r={selected ? 9 : 7}
                          fill={selected ? "#2f6e5a" : "#4d8f7a"}
                        />
                        <text x={positioned.x + 10} y={positioned.y + 4} fontSize="10">
                          {node.label}
                        </text>
                      </g>
                    );
                  })}
                </svg>
                <div className="status">
                  Keyboard: arrow keys move selection. Home/End jump to first/last visible node.
                </div>
                {selectedGraphNode ? (
                  <div className="status">
                    Selected: {selectedGraphNode.label} ({selectedGraphNode.group})
                    {selectedGraphNode.stage ? ` | ${selectedGraphNode.stage}` : ""}
                  </div>
                ) : (
                  <div className="status">No nodes match the current filter set.</div>
                )}
                <div className="status">
                  <strong>Drilldown</strong>
                  <div>{drilldownStatus}</div>
                  {drilldown ? (
                    <div>
                      <div>
                        <strong>{drilldown.title}</strong> ({drilldown.item_type})
                      </div>
                      <div>{drilldown.content}</div>
                      <div>Evidence: {drilldown.evidence_segment_ids.join(", ")}</div>
                    </div>
                  ) : null}
                </div>
                <div className="filter-grid">
                  <label>
                    Export view
                    <select
                      value={exportView}
                      onChange={(event) => setExportView(event.target.value as ExportView)}
                    >
                      <option value="graph">graph</option>
                      <option value="timeline">timeline</option>
                      <option value="theme-heatmap">theme-heatmap</option>
                    </select>
                  </label>
                  <label>
                    Export format
                    <select
                      value={exportFormat}
                      onChange={(event) => setExportFormat(event.target.value as ExportFormat)}
                    >
                      <option value="svg">svg</option>
                      <option value="png">png</option>
                    </select>
                  </label>
                  <div className="inline-actions">
                    <button type="button" className="muted" onClick={() => void onGenerateExportPreset()}>
                      Generate Export Preset
                    </button>
                    {exportHref ? (
                      <a className="export-link" href={exportHref} download={exportFilename}>
                        Download {exportFilename}
                      </a>
                    ) : null}
                  </div>
                </div>
                {exportPayloadPreview ? (
                  <details>
                    <summary>Export payload preview</summary>
                    <textarea readOnly rows={6} value={exportPayloadPreview} />
                  </details>
                ) : null}
                <details>
                  <summary>Graph SVG export</summary>
                  <textarea readOnly rows={6} value={graphSvg} />
                </details>
              </div>
            ) : null}
          </article>
        </div>
      </section>

      <section className="card">
        <h2>Good Essay Mode</h2>
        <div className="grid story-grid">
          <aside>
            <h3>Saved essays</h3>
            <button
              type="button"
              className="muted"
              onClick={() => {
                setSelectedEssayId(null);
                setEssayTitle("");
                setEssayDraftText("");
                setEssayBlueprintRaw(JSON.stringify(defaultEssayBlueprint(), null, 2));
                setEssayEvaluation(null);
              }}
            >
              New essay
            </button>
            <ul>
              {essays.map((essay) => (
                <li key={essay.essay_id}>
                  <button type="button" onClick={() => onSelectEssay(essay)} className="link-button">
                    {essay.title}
                  </button>
                </li>
              ))}
            </ul>
            {essayEvaluation ? (
              <div className="status">
                <strong>Latest evaluation</strong>
                <div>Passed: {essayEvaluation.passed ? "yes" : "no"}</div>
                <div>Score: {essayEvaluation.score.toFixed(1)}</div>
                <div>
                  Words: {essayEvaluation.word_count} | Citations: {essayEvaluation.citation_count}/
                  {essayEvaluation.required_citations}
                </div>
                <ul>
                  {essayEvaluation.checks.map((check) => (
                    <li key={`${check.code}-${check.message}`}>
                      {check.severity.toUpperCase()}: {check.message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </aside>

          <form onSubmit={onCreateOrUpdateEssay} className="stack">
            <label>
              Essay title
              <input value={essayTitle} onChange={(event) => setEssayTitle(event.target.value)} />
            </label>
            <label>
              Essay blueprint JSON
              <textarea
                rows={14}
                value={essayBlueprintRaw}
                onChange={(event) => setEssayBlueprintRaw(event.target.value)}
              />
            </label>
            <label>
              Draft text
              <textarea
                rows={10}
                value={essayDraftText}
                onChange={(event) => setEssayDraftText(event.target.value)}
              />
            </label>
            <div className="inline-actions">
              <button type="submit">{selectedEssay ? "Update Essay" : "Create Essay"}</button>
              <button type="button" className="muted" onClick={() => void onEvaluateEssay()}>
                Evaluate Essay
              </button>
            </div>
          </form>
        </div>
      </section>
    </main>
  );
};

export default App;
