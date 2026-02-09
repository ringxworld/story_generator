import type {
  AuthTokenResponse,
  DashboardArcPointResponse,
  DashboardDrilldownResponse,
  DashboardGraphExportResponse,
  DashboardPngExportResponse,
  DashboardGraphResponse,
  DashboardOverviewResponse,
  DashboardSvgExportResponse,
  DashboardThemeHeatmapCellResponse,
  DashboardTimelineLaneResponse,
  EssayBlueprint,
  EssayEvaluationResponse,
  EssayResponse,
  StoryAnalysisRunResponse,
  StoryBlueprint,
  StoryResponse,
  UserResponse,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || DEFAULT_API_BASE_URL;

const requestJson = async <T>(path: string, init: RequestInit = {}): Promise<T> => {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
};

export const register = async (email: string, password: string, displayName: string): Promise<UserResponse> =>
  requestJson<UserResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      display_name: displayName,
    }),
  });

export const login = async (email: string, password: string): Promise<AuthTokenResponse> =>
  requestJson<AuthTokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

export const me = async (token: string): Promise<UserResponse> =>
  requestJson<UserResponse>("/api/v1/me", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const listStories = async (token: string): Promise<StoryResponse[]> =>
  requestJson<StoryResponse[]>("/api/v1/stories", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const createStory = async (
  token: string,
  title: string,
  blueprint: StoryBlueprint,
): Promise<StoryResponse> =>
  requestJson<StoryResponse>("/api/v1/stories", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ title, blueprint }),
  });

export const updateStory = async (
  token: string,
  storyId: string,
  title: string,
  blueprint: StoryBlueprint,
): Promise<StoryResponse> =>
  requestJson<StoryResponse>(`/api/v1/stories/${storyId}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ title, blueprint }),
  });

export const listEssays = async (token: string): Promise<EssayResponse[]> =>
  requestJson<EssayResponse[]>("/api/v1/essays", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const createEssay = async (
  token: string,
  title: string,
  blueprint: EssayBlueprint,
  draftText: string,
): Promise<EssayResponse> =>
  requestJson<EssayResponse>("/api/v1/essays", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ title, blueprint, draft_text: draftText }),
  });

export const updateEssay = async (
  token: string,
  essayId: string,
  title: string,
  blueprint: EssayBlueprint,
  draftText: string,
): Promise<EssayResponse> =>
  requestJson<EssayResponse>(`/api/v1/essays/${essayId}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ title, blueprint, draft_text: draftText }),
  });

export const evaluateEssay = async (
  token: string,
  essayId: string,
  draftText?: string,
): Promise<EssayEvaluationResponse> =>
  requestJson<EssayEvaluationResponse>(`/api/v1/essays/${essayId}/evaluate`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ draft_text: draftText }),
  });

export const runStoryAnalysis = async (
  token: string,
  storyId: string,
  payload: { source_text?: string; source_type?: "text" | "document" | "transcript"; target_language?: string } = {},
): Promise<StoryAnalysisRunResponse> =>
  requestJson<StoryAnalysisRunResponse>(`/api/v1/stories/${storyId}/analysis/run`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });

export const getLatestStoryAnalysis = async (token: string, storyId: string): Promise<StoryAnalysisRunResponse> =>
  requestJson<StoryAnalysisRunResponse>(`/api/v1/stories/${storyId}/analysis/latest`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const getDashboardOverview = async (
  token: string,
  storyId: string,
): Promise<DashboardOverviewResponse> =>
  requestJson<DashboardOverviewResponse>(`/api/v1/stories/${storyId}/dashboard/overview`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const getDashboardTimeline = async (
  token: string,
  storyId: string,
): Promise<DashboardTimelineLaneResponse[]> =>
  requestJson<DashboardTimelineLaneResponse[]>(`/api/v1/stories/${storyId}/dashboard/timeline`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const getDashboardThemeHeatmap = async (
  token: string,
  storyId: string,
): Promise<DashboardThemeHeatmapCellResponse[]> =>
  requestJson<DashboardThemeHeatmapCellResponse[]>(
    `/api/v1/stories/${storyId}/dashboard/themes/heatmap`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );

export const getDashboardArcs = async (
  token: string,
  storyId: string,
): Promise<DashboardArcPointResponse[]> =>
  requestJson<DashboardArcPointResponse[]>(`/api/v1/stories/${storyId}/dashboard/arcs`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const getDashboardDrilldown = async (
  token: string,
  storyId: string,
  itemId: string,
): Promise<DashboardDrilldownResponse> =>
  requestJson<DashboardDrilldownResponse>(`/api/v1/stories/${storyId}/dashboard/drilldown/${itemId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const getDashboardGraph = async (
  token: string,
  storyId: string,
): Promise<DashboardGraphResponse> =>
  requestJson<DashboardGraphResponse>(`/api/v1/stories/${storyId}/dashboard/graph`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const exportDashboardGraphSvg = async (
  token: string,
  storyId: string,
): Promise<DashboardGraphExportResponse> =>
  requestJson<DashboardGraphExportResponse>(`/api/v1/stories/${storyId}/dashboard/graph/export.svg`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const exportDashboardGraphPng = async (
  token: string,
  storyId: string,
): Promise<DashboardPngExportResponse> =>
  requestJson<DashboardPngExportResponse>(`/api/v1/stories/${storyId}/dashboard/graph/export.png`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const exportDashboardTimelineSvg = async (
  token: string,
  storyId: string,
): Promise<DashboardSvgExportResponse> =>
  requestJson<DashboardSvgExportResponse>(`/api/v1/stories/${storyId}/dashboard/timeline/export.svg`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const exportDashboardTimelinePng = async (
  token: string,
  storyId: string,
): Promise<DashboardPngExportResponse> =>
  requestJson<DashboardPngExportResponse>(`/api/v1/stories/${storyId}/dashboard/timeline/export.png`, {
    headers: { Authorization: `Bearer ${token}` },
  });

export const exportDashboardThemeHeatmapSvg = async (
  token: string,
  storyId: string,
): Promise<DashboardSvgExportResponse> =>
  requestJson<DashboardSvgExportResponse>(
    `/api/v1/stories/${storyId}/dashboard/themes/heatmap/export.svg`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );

export const exportDashboardThemeHeatmapPng = async (
  token: string,
  storyId: string,
): Promise<DashboardPngExportResponse> =>
  requestJson<DashboardPngExportResponse>(
    `/api/v1/stories/${storyId}/dashboard/themes/heatmap/export.png`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
