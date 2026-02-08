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
