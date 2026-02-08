import {
  apiBaseUrl,
  createEssay,
  createStory,
  evaluateEssay,
  listEssays,
  listStories,
  login,
  me,
  register,
  updateEssay,
  updateStory,
} from "./api";
import type { EssayBlueprint, StoryBlueprint } from "./types";

const asResponse = (value: Partial<Response>): Response => value as Response;

describe("api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("exposes the default API base URL when no environment override exists", () => {
    expect(apiBaseUrl).toBe("http://127.0.0.1:8000");
  });

  it("registers a user with the expected payload", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      asResponse({
        ok: true,
        json: async () => ({
          user_id: "u-1",
          email: "writer@example.com",
          display_name: "Writer",
          created_at_utc: "2026-01-01T00:00:00Z",
        }),
      }),
    );

    const response = await register("writer@example.com", "secret123", "Writer");

    expect(response.display_name).toBe("Writer");
    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBaseUrl}/api/v1/auth/register`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "writer@example.com",
          password: "secret123",
          display_name: "Writer",
        }),
      }),
    );
  });

  it("logs in and forwards credentials", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      asResponse({
        ok: true,
        json: async () => ({
          access_token: "token-1",
          token_type: "bearer",
          expires_at_utc: "2026-01-01T01:00:00Z",
        }),
      }),
    );

    const response = await login("writer@example.com", "secret123");

    expect(response.access_token).toBe("token-1");
    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBaseUrl}/api/v1/auth/login`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "writer@example.com",
          password: "secret123",
        }),
      }),
    );
  });

  it("loads the authenticated user profile", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      asResponse({
        ok: true,
        json: async () => ({
          user_id: "u-1",
          email: "writer@example.com",
          display_name: "Writer",
          created_at_utc: "2026-01-01T00:00:00Z",
        }),
      }),
    );

    await me("token-abc");

    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBaseUrl}/api/v1/me`,
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token-abc",
        }),
      }),
    );
  });

  it("creates and updates stories with authenticated requests", async () => {
    const storyBlueprint: StoryBlueprint = {
      premise: "Premise",
      themes: [{ key: "memory", statement: "Truth decays", priority: 1 }],
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
          title: "Start",
          objective: "Open the case",
          required_themes: ["memory"],
          participating_characters: ["rhea"],
          prerequisites: [],
          draft_text: null,
        },
      ],
      canon_rules: ["No supernatural causes."],
    };

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        asResponse({
          ok: true,
          json: async () => ({
            story_id: "s-1",
            owner_id: "u-1",
            title: "Ledger",
            blueprint: storyBlueprint,
            created_at_utc: "2026-01-01T00:00:00Z",
            updated_at_utc: "2026-01-01T00:00:00Z",
          }),
        }),
      )
      .mockResolvedValueOnce(
        asResponse({
          ok: true,
          json: async () => ({
            story_id: "s-1",
            owner_id: "u-1",
            title: "Ledger v2",
            blueprint: storyBlueprint,
            created_at_utc: "2026-01-01T00:00:00Z",
            updated_at_utc: "2026-01-01T02:00:00Z",
          }),
        }),
      );

    await createStory("token-abc", "Ledger", storyBlueprint);
    await updateStory("token-abc", "s-1", "Ledger v2", storyBlueprint);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      `${apiBaseUrl}/api/v1/stories`,
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer token-abc",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `${apiBaseUrl}/api/v1/stories/s-1`,
      expect.objectContaining({
        method: "PUT",
        headers: expect.objectContaining({
          Authorization: "Bearer token-abc",
        }),
      }),
    );
  });

  it("lists stories for a signed-in user", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      asResponse({
        ok: true,
        json: async () => [],
      }),
    );

    await listStories("token-abc");

    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBaseUrl}/api/v1/stories`,
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token-abc",
        }),
      }),
    );
  });

  it("creates, updates, lists, and evaluates essays", async () => {
    const essayBlueprint: EssayBlueprint = {
      prompt: "Write with constraints.",
      policy: {
        thesis_statement: "Constraints reduce drift.",
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
        banned_phrases: [],
        required_citations: 1,
      },
      rubric: ["clear thesis"],
    };

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        asResponse({
          ok: true,
          json: async () => ({
            essay_id: "e-1",
            owner_id: "u-1",
            title: "Essay",
            blueprint: essayBlueprint,
            draft_text: "introduction: according to [1]...",
            created_at_utc: "2026-01-01T00:00:00Z",
            updated_at_utc: "2026-01-01T00:00:00Z",
          }),
        }),
      )
      .mockResolvedValueOnce(
        asResponse({
          ok: true,
          json: async () => ({
            essay_id: "e-1",
            owner_id: "u-1",
            title: "Essay v2",
            blueprint: essayBlueprint,
            draft_text: "introduction: according to [1]...",
            created_at_utc: "2026-01-01T00:00:00Z",
            updated_at_utc: "2026-01-01T02:00:00Z",
          }),
        }),
      )
      .mockResolvedValueOnce(
        asResponse({
          ok: true,
          json: async () => [],
        }),
      )
      .mockResolvedValueOnce(
        asResponse({
          ok: true,
          json: async () => ({
            essay_id: "e-1",
            owner_id: "u-1",
            passed: true,
            score: 92.5,
            word_count: 440,
            citation_count: 2,
            required_citations: 1,
            checks: [],
          }),
        }),
      );

    await createEssay("token-abc", "Essay", essayBlueprint, "draft");
    await updateEssay("token-abc", "e-1", "Essay v2", essayBlueprint, "draft");
    await listEssays("token-abc");
    await evaluateEssay("token-abc", "e-1", "draft");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      `${apiBaseUrl}/api/v1/essays`,
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `${apiBaseUrl}/api/v1/essays/e-1`,
      expect.objectContaining({
        method: "PUT",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `${apiBaseUrl}/api/v1/essays`,
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token-abc",
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      `${apiBaseUrl}/api/v1/essays/e-1/evaluate`,
      expect.objectContaining({
        method: "POST",
      }),
    );
  });

  it("surfaces API error details when a request fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      asResponse({
        ok: false,
        status: 401,
        text: async () => "invalid credentials",
      }),
    );

    await expect(login("writer@example.com", "wrong")).rejects.toThrow("invalid credentials");
  });

  it("falls back to HTTP status when error body is empty", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      asResponse({
        ok: false,
        status: 500,
        text: async () => "",
      }),
    );

    await expect(me("token-abc")).rejects.toThrow("Request failed with 500");
  });
});
