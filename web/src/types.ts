export type ThemeBlock = {
  key: string;
  statement: string;
  priority: number;
};

export type CharacterBlock = {
  key: string;
  role: string;
  motivation: string;
  voice_markers: string[];
  relationships: Record<string, string>;
};

export type ChapterBlock = {
  key: string;
  title: string;
  objective: string;
  required_themes: string[];
  participating_characters: string[];
  prerequisites: string[];
  draft_text: string | null;
};

export type StoryBlueprint = {
  premise: string;
  themes: ThemeBlock[];
  characters: CharacterBlock[];
  chapters: ChapterBlock[];
  canon_rules: string[];
};

export type StoryResponse = {
  story_id: string;
  owner_id: string;
  title: string;
  blueprint: StoryBlueprint;
  created_at_utc: string;
  updated_at_utc: string;
};

export type UserResponse = {
  user_id: string;
  email: string;
  display_name: string;
  created_at_utc: string;
};

export type AuthTokenResponse = {
  access_token: string;
  token_type: string;
  expires_at_utc: string;
};

export type EssaySectionRequirement = {
  key: string;
  purpose: string;
  min_paragraphs: number;
  required_terms: string[];
};

export type EssayPolicy = {
  thesis_statement: string;
  audience: string;
  tone: string;
  min_words: number;
  max_words: number;
  required_sections: EssaySectionRequirement[];
  banned_phrases: string[];
  required_citations: number;
};

export type EssayBlueprint = {
  prompt: string;
  policy: EssayPolicy;
  rubric: string[];
};

export type EssayResponse = {
  essay_id: string;
  owner_id: string;
  title: string;
  blueprint: EssayBlueprint;
  draft_text: string;
  created_at_utc: string;
  updated_at_utc: string;
};

export type EssayQualityCheckResponse = {
  code: string;
  severity: "error" | "warning";
  message: string;
};

export type EssayEvaluationResponse = {
  essay_id: string;
  owner_id: string;
  passed: boolean;
  score: number;
  word_count: number;
  citation_count: number;
  required_citations: number;
  checks: EssayQualityCheckResponse[];
};

export type StoryAnalysisGateResponse = {
  passed: boolean;
  confidence_floor: number;
  hallucination_risk: number;
  translation_quality: number;
  reasons: string[];
};

export type StoryAnalysisRunResponse = {
  run_id: string;
  story_id: string;
  owner_id: string;
  schema_version: string;
  analyzed_at_utc: string;
  source_language: string;
  target_language: string;
  segment_count: number;
  event_count: number;
  beat_count: number;
  theme_count: number;
  insight_count: number;
  quality_gate: StoryAnalysisGateResponse;
};

export type DashboardOverviewResponse = {
  title: string;
  macro_thesis: string;
  confidence_floor: number;
  quality_passed: boolean;
  events_count: number;
  beats_count: number;
  themes_count: number;
};

export type DashboardTimelineLaneResponse = {
  lane: string;
  items: Array<Record<string, string | number | null>>;
};

export type DashboardThemeHeatmapCellResponse = {
  theme: string;
  stage: string;
  intensity: number;
};

export type DashboardArcPointResponse = {
  lane: string;
  stage: string;
  value: number;
  label: string;
};

export type DashboardDrilldownResponse = {
  item_id: string;
  item_type: string;
  title: string;
  content: string;
  evidence_segment_ids: string[];
};

export type DashboardGraphNodeResponse = {
  id: string;
  label: string;
  group: string;
  stage: string | null;
  layout_x?: number | null;
  layout_y?: number | null;
};

export type DashboardGraphEdgeResponse = {
  source: string;
  target: string;
  relation: string;
  weight: number;
};

export type DashboardGraphResponse = {
  nodes: DashboardGraphNodeResponse[];
  edges: DashboardGraphEdgeResponse[];
};

export type DashboardSvgExportResponse = {
  format: "svg";
  svg: string;
};

export type DashboardPngExportResponse = {
  format: "png";
  png_base64: string;
};

export type DashboardGraphExportResponse = DashboardSvgExportResponse;
