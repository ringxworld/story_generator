import type { AuthTokenResponse, StoryBlueprint, StoryResponse, UserResponse } from "./types";

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
