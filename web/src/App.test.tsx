import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import App from "./App";
import * as api from "./api";
import type { EssayBlueprint, EssayEvaluationResponse, EssayResponse, StoryBlueprint, StoryResponse } from "./types";

vi.mock("./api", () => ({
  apiBaseUrl: "http://127.0.0.1:8000",
  register: vi.fn(),
  login: vi.fn(),
  me: vi.fn(),
  listStories: vi.fn(),
  createStory: vi.fn(),
  updateStory: vi.fn(),
  runStoryAnalysis: vi.fn(),
  getLatestStoryAnalysis: vi.fn(),
  getDashboardOverview: vi.fn(),
  getDashboardTimeline: vi.fn(),
  getDashboardThemeHeatmap: vi.fn(),
  getDashboardArcs: vi.fn(),
  getDashboardDrilldown: vi.fn(),
  getDashboardGraph: vi.fn(),
  exportDashboardGraphSvg: vi.fn(),
  exportDashboardGraphPng: vi.fn(),
  exportDashboardTimelineSvg: vi.fn(),
  exportDashboardTimelinePng: vi.fn(),
  exportDashboardThemeHeatmapSvg: vi.fn(),
  exportDashboardThemeHeatmapPng: vi.fn(),
  listEssays: vi.fn(),
  createEssay: vi.fn(),
  updateEssay: vi.fn(),
  evaluateEssay: vi.fn(),
}));

const mockedApi = vi.mocked(api);

const sampleBlueprint: StoryBlueprint = {
  premise: "A city questions its own records.",
  themes: [{ key: "memory", statement: "Memory can be altered.", priority: 1 }],
  characters: [
    {
      key: "rhea",
      role: "investigator",
      motivation: "Find the ledger",
      voice_markers: [],
      relationships: {},
    },
  ],
  chapters: [
    {
      key: "ch01",
      title: "The Missing Ledger",
      objective: "Introduce contradiction",
      required_themes: ["memory"],
      participating_characters: ["rhea"],
      prerequisites: [],
      draft_text: null,
    },
  ],
  canon_rules: ["No supernatural causes."],
};

const sampleStory: StoryResponse = {
  story_id: "story-1",
  owner_id: "user-1",
  title: "The Missing Ledger",
  blueprint: sampleBlueprint,
  created_at_utc: "2026-01-01T00:00:00Z",
  updated_at_utc: "2026-01-01T00:00:00Z",
};

const sampleEssayBlueprint: EssayBlueprint = {
  prompt: "Write a coherent argument.",
  policy: {
    thesis_statement: "Constraint-first drafting improves coherence.",
    audience: "technical readers",
    tone: "analytical",
    min_words: 300,
    max_words: 900,
    required_sections: [
      {
        key: "introduction",
        purpose: "Frame claim",
        min_paragraphs: 1,
        required_terms: [],
      },
    ],
    banned_phrases: ["as an ai language model"],
    required_citations: 1,
  },
  rubric: ["clear thesis"],
};

const sampleEssay: EssayResponse = {
  essay_id: "essay-1",
  owner_id: "user-1",
  title: "Constraint Drafting",
  blueprint: sampleEssayBlueprint,
  draft_text: "introduction: according to [1], constraints preserve coherence.",
  created_at_utc: "2026-01-01T00:00:00Z",
  updated_at_utc: "2026-01-01T00:00:00Z",
};

const sampleEvaluation: EssayEvaluationResponse = {
  essay_id: "essay-1",
  owner_id: "user-1",
  passed: true,
  score: 100,
  word_count: 320,
  citation_count: 1,
  required_citations: 1,
  checks: [],
};

const createDeferred = <T,>() => {
  let resolve: ((value: T | PromiseLike<T>) => void) | undefined;
  let reject: ((reason?: unknown) => void) | undefined;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return {
    promise,
    resolve: (value: T | PromiseLike<T>) => resolve?.(value),
    reject: (reason?: unknown) => reject?.(reason),
  };
};

describe("App", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    vi.clearAllMocks();
    mockedApi.listStories.mockResolvedValue([]);
    mockedApi.listEssays.mockResolvedValue([]);
    mockedApi.getLatestStoryAnalysis.mockRejectedValue(new Error("not found"));
    mockedApi.getDashboardOverview.mockRejectedValue(new Error("not found"));
    mockedApi.getDashboardTimeline.mockRejectedValue(new Error("not found"));
    mockedApi.getDashboardThemeHeatmap.mockRejectedValue(new Error("not found"));
    mockedApi.getDashboardArcs.mockRejectedValue(new Error("not found"));
    mockedApi.getDashboardDrilldown.mockRejectedValue(new Error("404"));
    mockedApi.getDashboardGraph.mockRejectedValue(new Error("not found"));
    mockedApi.exportDashboardGraphSvg.mockRejectedValue(new Error("not found"));
    mockedApi.exportDashboardGraphPng.mockRejectedValue(new Error("not found"));
    mockedApi.exportDashboardTimelineSvg.mockRejectedValue(new Error("not found"));
    mockedApi.exportDashboardTimelinePng.mockRejectedValue(new Error("not found"));
    mockedApi.exportDashboardThemeHeatmapSvg.mockRejectedValue(new Error("not found"));
    mockedApi.exportDashboardThemeHeatmapPng.mockRejectedValue(new Error("not found"));
  });

  it("renders offline demo mode when query flag is set", () => {
    window.history.replaceState({}, "", "/?demo=1");
    render(<App />);
    expect(screen.getByText("Offline Demo Mode")).toBeInTheDocument();
    expect(screen.getByText("Offline demo mode for GitHub Pages. No backend required.")).toBeInTheDocument();
  });

  it("renders studio heading and auth section", () => {
    render(<App />);
    expect(screen.getByText("story_gen studio")).toBeInTheDocument();
    expect(screen.getByText("Auth")).toBeInTheDocument();
    expect(screen.getByText("Story Blueprints")).toBeInTheDocument();
    expect(screen.getByText("Good Essay Mode")).toBeInTheDocument();
  });

  it("defaults to dark mode and toggles to light mode", async () => {
    render(<App />);
    await waitFor(() => {
      expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    });

    fireEvent.click(screen.getByRole("button", { name: "Light mode" }));

    await waitFor(() => {
      expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    });
    expect(localStorage.getItem("story_gen.theme")).toBe("light");
    expect(screen.getByRole("button", { name: "Dark mode" })).toBeInTheDocument();
  });

  it("shows a guardrail message when saving without auth", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Create Story" }));

    await waitFor(() => {
      expect(screen.getByText("Sign in before saving stories.")).toBeInTheDocument();
    });
  });

  it("registers a user and updates status text", async () => {
    mockedApi.register.mockResolvedValue({
      user_id: "user-1",
      email: "writer@example.com",
      display_name: "Writer",
      created_at_utc: "2026-01-01T00:00:00Z",
    });

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[0], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[0], { target: { value: "secret123" } });
    fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Writer" } });
    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => {
      expect(screen.getByText("Registered successfully. You can now log in.")).toBeInTheDocument();
    });
    expect(mockedApi.register).toHaveBeenCalledWith("writer@example.com", "secret123", "Writer");
  });

  it("handles registration errors", async () => {
    mockedApi.register.mockRejectedValue(new Error("email already exists"));

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[0], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[0], { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => {
      expect(screen.getByText("Registration failed: email already exists")).toBeInTheDocument();
    });
  });

  it("logs in, stores token, and signs out cleanly", async () => {
    mockedApi.login.mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_at_utc: "2026-01-01T01:00:00Z",
    });
    mockedApi.me.mockResolvedValue({
      user_id: "user-1",
      email: "writer@example.com",
      display_name: "Writer",
      created_at_utc: "2026-01-01T00:00:00Z",
    });
    mockedApi.listStories.mockResolvedValue([sampleStory]);

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[1], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[1], { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByText("Signed in as Writer.")).toBeInTheDocument();
    });
    expect(localStorage.getItem("story_gen.token")).toBe("token-abc");
    expect(screen.getByRole("button", { name: "The Missing Ledger" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Sign Out" }));
    expect(screen.getByText("Signed out.")).toBeInTheDocument();
    expect(localStorage.getItem("story_gen.token")).toBeNull();
  });

  it("creates a story after login", async () => {
    mockedApi.login.mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_at_utc: "2026-01-01T01:00:00Z",
    });
    mockedApi.me.mockResolvedValue({
      user_id: "user-1",
      email: "writer@example.com",
      display_name: "Writer",
      created_at_utc: "2026-01-01T00:00:00Z",
    });
    mockedApi.listStories.mockResolvedValue([]);
    mockedApi.createStory.mockResolvedValue(sampleStory);

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[1], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[1], { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByText("Signed in as Writer.")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "The Missing Ledger" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Story" }));

    await waitFor(() => {
      expect(screen.getByText("Created story: The Missing Ledger")).toBeInTheDocument();
    });
    expect(mockedApi.createStory).toHaveBeenCalled();
  });

  it("updates an existing story after selection", async () => {
    mockedApi.login.mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_at_utc: "2026-01-01T01:00:00Z",
    });
    mockedApi.me.mockResolvedValue({
      user_id: "user-1",
      email: "writer@example.com",
      display_name: "Writer",
      created_at_utc: "2026-01-01T00:00:00Z",
    });
    mockedApi.listStories.mockResolvedValue([sampleStory]);
    mockedApi.updateStory.mockResolvedValue({
      ...sampleStory,
      title: "The Missing Ledger Revised",
    });

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[1], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[1], { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "The Missing Ledger" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "The Missing Ledger" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "The Missing Ledger Revised" } });
    fireEvent.click(screen.getByRole("button", { name: "Update Story" }));

    await waitFor(() => {
      expect(screen.getByText("Updated story: The Missing Ledger Revised")).toBeInTheDocument();
    });
    expect(mockedApi.updateStory).toHaveBeenCalledWith(
      "token-abc",
      "story-1",
      "The Missing Ledger Revised",
      expect.any(Object),
    );
  });

  it("keeps save status when a pending dashboard refresh fails later", async () => {
    const latestRunDeferred = createDeferred<never>();
    mockedApi.login.mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_at_utc: "2026-01-01T01:00:00Z",
    });
    mockedApi.me.mockResolvedValue({
      user_id: "user-1",
      email: "writer@example.com",
      display_name: "Writer",
      created_at_utc: "2026-01-01T00:00:00Z",
    });
    mockedApi.listStories.mockResolvedValue([sampleStory]);
    mockedApi.getLatestStoryAnalysis.mockReturnValue(latestRunDeferred.promise);
    mockedApi.getDashboardOverview.mockResolvedValue({
      title: "Story Intelligence Overview",
      macro_thesis: "Memory and truth collide.",
      confidence_floor: 0.7,
      quality_passed: true,
      events_count: 2,
      beats_count: 2,
      themes_count: 1,
    });
    mockedApi.getDashboardTimeline.mockResolvedValue([{ lane: "narrative_order", items: [] }]);
    mockedApi.getDashboardThemeHeatmap.mockResolvedValue([]);
    mockedApi.getDashboardArcs.mockResolvedValue([]);
    mockedApi.getDashboardGraph.mockResolvedValue({ nodes: [], edges: [] });
    mockedApi.exportDashboardGraphSvg.mockResolvedValue({ format: "svg", svg: "<svg></svg>" });
    mockedApi.updateStory.mockResolvedValue({
      ...sampleStory,
      title: "The Missing Ledger Revised",
    });

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[1], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[1], { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "The Missing Ledger" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "The Missing Ledger" }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "The Missing Ledger Revised" } });
    fireEvent.click(screen.getByRole("button", { name: "Update Story" }));

    await waitFor(() => {
      expect(screen.getByText("Updated story: The Missing Ledger Revised")).toBeInTheDocument();
    });

    latestRunDeferred.reject(new Error("no analysis run yet"));

    await waitFor(() => {
      expect(screen.getByText("Updated story: The Missing Ledger Revised")).toBeInTheDocument();
    });
  });

  it("handles login errors", async () => {
    mockedApi.login.mockRejectedValue(new Error("invalid credentials"));

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[1], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[1], { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByText("Login failed: invalid credentials")).toBeInTheDocument();
    });
  });

  it("shows essay auth guardrail when saving without auth", async () => {
    render(<App />);

    fireEvent.change(screen.getByLabelText("Essay title"), { target: { value: "Constraint Drafting" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Essay" }));

    await waitFor(() => {
      expect(screen.getByText("Sign in before saving essays.")).toBeInTheDocument();
    });
  });

  it("creates and evaluates an essay after login", async () => {
    mockedApi.login.mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_at_utc: "2026-01-01T01:00:00Z",
    });
    mockedApi.me.mockResolvedValue({
      user_id: "user-1",
      email: "writer@example.com",
      display_name: "Writer",
      created_at_utc: "2026-01-01T00:00:00Z",
    });
    mockedApi.createEssay.mockResolvedValue(sampleEssay);
    mockedApi.listEssays.mockResolvedValue([sampleEssay]);
    mockedApi.evaluateEssay.mockResolvedValue(sampleEvaluation);

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[1], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[1], { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByText("Signed in as Writer.")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Essay title"), { target: { value: "Constraint Drafting" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Essay" }));

    await waitFor(() => {
      expect(screen.getByText("Created essay: Constraint Drafting")).toBeInTheDocument();
    });
    expect(mockedApi.createEssay).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Constraint Drafting" }));
    fireEvent.click(screen.getByRole("button", { name: "Evaluate Essay" }));

    await waitFor(() => {
      expect(screen.getByText("Essay passed checks with score 100.0.")).toBeInTheDocument();
    });
    expect(mockedApi.evaluateEssay).toHaveBeenCalledWith("token-abc", "essay-1", expect.any(String));
  });

  it("runs story analysis and loads dashboard projections", async () => {
    mockedApi.login.mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_at_utc: "2026-01-01T01:00:00Z",
    });
    mockedApi.me.mockResolvedValue({
      user_id: "user-1",
      email: "writer@example.com",
      display_name: "Writer",
      created_at_utc: "2026-01-01T00:00:00Z",
    });
    mockedApi.listStories.mockResolvedValue([sampleStory]);
    mockedApi.runStoryAnalysis.mockResolvedValue({
      run_id: "run-1",
      story_id: "story-1",
      owner_id: "user-1",
      schema_version: "story_analysis.v1",
      analyzed_at_utc: "2026-01-01T00:00:00Z",
      source_language: "en",
      target_language: "en",
      segment_count: 1,
      event_count: 2,
      beat_count: 2,
      theme_count: 1,
      insight_count: 4,
      quality_gate: {
        passed: true,
        confidence_floor: 0.7,
        hallucination_risk: 0.1,
        translation_quality: 1,
        reasons: [],
      },
    });
    mockedApi.getLatestStoryAnalysis.mockResolvedValue({
      run_id: "run-1",
      story_id: "story-1",
      owner_id: "user-1",
      schema_version: "story_analysis.v1",
      analyzed_at_utc: "2026-01-01T00:00:00Z",
      source_language: "en",
      target_language: "en",
      segment_count: 1,
      event_count: 2,
      beat_count: 2,
      theme_count: 1,
      insight_count: 4,
      quality_gate: {
        passed: true,
        confidence_floor: 0.7,
        hallucination_risk: 0.1,
        translation_quality: 1,
        reasons: [],
      },
    });
    mockedApi.getDashboardOverview.mockResolvedValue({
      title: "Story Intelligence Overview",
      macro_thesis: "Memory and truth collide.",
      confidence_floor: 0.7,
      quality_passed: true,
      events_count: 2,
      beats_count: 2,
      themes_count: 1,
    });
    mockedApi.getDashboardTimeline.mockResolvedValue([{ lane: "narrative_order", items: [] }]);
    mockedApi.getDashboardThemeHeatmap.mockResolvedValue([
      { theme: "memory", stage: "setup", intensity: 1 },
    ]);
    mockedApi.getDashboardArcs.mockResolvedValue([{ lane: "emotion", stage: "setup", value: 0.6, label: "positive" }]);
    mockedApi.getDashboardGraph.mockResolvedValue({
      nodes: [{ id: "n1", label: "memory", group: "theme", stage: "setup" }],
      edges: [],
    });
    mockedApi.exportDashboardGraphSvg.mockResolvedValue({
      format: "svg",
      svg: "<svg></svg>",
    });

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[1], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[1], { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "The Missing Ledger" })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "The Missing Ledger" }));
    fireEvent.click(screen.getByRole("button", { name: "Run Analysis" }));

    await waitFor(() => {
      expect(screen.getByText("Analysis complete (2 events).")).toBeInTheDocument();
    });
    expect(mockedApi.runStoryAnalysis).toHaveBeenCalledWith("token-abc", "story-1", {});
    expect(screen.getByText("Interactive Graph")).toBeInTheDocument();
  });

  it("supports graph keyboard navigation, drilldown lookup, and export presets", async () => {
    mockedApi.login.mockResolvedValue({
      access_token: "token-abc",
      token_type: "bearer",
      expires_at_utc: "2026-01-01T01:00:00Z",
    });
    mockedApi.me.mockResolvedValue({
      user_id: "user-1",
      email: "writer@example.com",
      display_name: "Writer",
      created_at_utc: "2026-01-01T00:00:00Z",
    });
    mockedApi.listStories.mockResolvedValue([sampleStory]);
    mockedApi.getLatestStoryAnalysis.mockResolvedValue({
      run_id: "run-1",
      story_id: "story-1",
      owner_id: "user-1",
      schema_version: "story_analysis.v1",
      analyzed_at_utc: "2026-01-01T00:00:00Z",
      source_language: "en",
      target_language: "en",
      segment_count: 1,
      event_count: 2,
      beat_count: 2,
      theme_count: 1,
      insight_count: 4,
      quality_gate: {
        passed: true,
        confidence_floor: 0.7,
        hallucination_risk: 0.1,
        translation_quality: 1,
        reasons: [],
      },
    });
    mockedApi.getDashboardOverview.mockResolvedValue({
      title: "Story Intelligence Overview",
      macro_thesis: "Memory and truth collide.",
      confidence_floor: 0.7,
      quality_passed: true,
      events_count: 2,
      beats_count: 2,
      themes_count: 1,
    });
    mockedApi.getDashboardTimeline.mockResolvedValue([{ lane: "narrative_order", items: [{ id: "p1", label: "A", order: 1, time: null }] }]);
    mockedApi.getDashboardThemeHeatmap.mockResolvedValue([{ theme: "memory", stage: "setup", intensity: 1 }]);
    mockedApi.getDashboardArcs.mockResolvedValue([{ lane: "character:rhea", stage: "setup", value: 0.6, label: "positive" }]);
    mockedApi.getDashboardGraph.mockResolvedValue({
      nodes: [
        { id: "theme_memory", label: "memory", group: "theme", stage: "setup" },
        { id: "beat_1", label: "B1", group: "beat", stage: "setup" },
      ],
      edges: [{ source: "theme_memory", target: "beat_1", relation: "expressed_in", weight: 0.7 }],
    });
    mockedApi.exportDashboardGraphSvg.mockResolvedValue({
      format: "svg",
      svg: "<svg></svg>",
    });
    mockedApi.getDashboardDrilldown.mockResolvedValue({
      item_id: "theme:theme_memory",
      item_type: "theme",
      title: "Theme: memory",
      content: "detail",
      evidence_segment_ids: ["seg_01"],
    });
    mockedApi.exportDashboardTimelineSvg.mockResolvedValue({
      format: "svg",
      svg: "<svg>timeline</svg>",
    });

    render(<App />);

    fireEvent.change(screen.getAllByLabelText("Email")[1], { target: { value: "writer@example.com" } });
    fireEvent.change(screen.getAllByLabelText("Password")[1], { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "The Missing Ledger" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "The Missing Ledger" }));

    await waitFor(() => {
      expect(screen.getByText("Interactive Graph")).toBeInTheDocument();
    });

    fireEvent.keyDown(screen.getByRole("img", { name: "story-graph" }), { key: "ArrowRight" });

    await waitFor(() => {
      expect(screen.getByText(/Loaded drilldown:/)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Export view"), { target: { value: "timeline" } });
    fireEvent.change(screen.getByLabelText("Export format"), { target: { value: "svg" } });
    fireEvent.click(screen.getByRole("button", { name: "Generate Export Preset" }));

    await waitFor(() => {
      expect(mockedApi.exportDashboardTimelineSvg).toHaveBeenCalledWith("token-abc", "story-1");
    });
  });
});
