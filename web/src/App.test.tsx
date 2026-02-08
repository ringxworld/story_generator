import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import App from "./App";
import * as api from "./api";
import type { StoryBlueprint, StoryResponse } from "./types";

vi.mock("./api", () => ({
  apiBaseUrl: "http://127.0.0.1:8000",
  register: vi.fn(),
  login: vi.fn(),
  me: vi.fn(),
  listStories: vi.fn(),
  createStory: vi.fn(),
  updateStory: vi.fn(),
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

describe("App", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    mockedApi.listStories.mockResolvedValue([]);
  });

  it("renders studio heading and auth section", () => {
    render(<App />);
    expect(screen.getByText("story_gen studio")).toBeInTheDocument();
    expect(screen.getByText("Auth")).toBeInTheDocument();
    expect(screen.getByText("Story Blueprints")).toBeInTheDocument();
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
});
