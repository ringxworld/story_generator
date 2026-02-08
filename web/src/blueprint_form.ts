import type { StoryBlueprint } from "./types";

export type StoryFormState = {
  title: string;
  premise: string;
  canonRulesRaw: string;
  themesRaw: string;
  charactersRaw: string;
  chaptersRaw: string;
};

const splitLines = (raw: string): string[] =>
  raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

const splitCsv = (raw: string): string[] =>
  raw
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

export const emptyStoryForm = (): StoryFormState => ({
  title: "",
  premise: "",
  canonRulesRaw: "",
  themesRaw: "",
  charactersRaw: "",
  chaptersRaw: "",
});

export const buildBlueprintFromForm = (form: StoryFormState): StoryBlueprint => {
  const themes = splitLines(form.themesRaw).map((line) => {
    const [key, statement, priorityRaw] = line.split("|").map((part) => part.trim());
    if (!key || !statement) {
      throw new Error("Theme rows must use: key|statement|priority");
    }
    return {
      key,
      statement,
      priority: priorityRaw ? Number.parseInt(priorityRaw, 10) : 1,
    };
  });

  const characters = splitLines(form.charactersRaw).map((line) => {
    const [key, role, motivation] = line.split("|").map((part) => part.trim());
    if (!key || !role || !motivation) {
      throw new Error("Character rows must use: key|role|motivation");
    }
    return {
      key,
      role,
      motivation,
      voice_markers: [],
      relationships: {},
    };
  });

  const chapters = splitLines(form.chaptersRaw).map((line) => {
    const [key, title, objective, themesCsv, charsCsv, prereqCsv] = line
      .split("|")
      .map((part) => part.trim());
    if (!key || !title || !objective) {
      throw new Error(
        "Chapter rows must use: key|title|objective|required_themes_csv|characters_csv|prerequisites_csv",
      );
    }
    return {
      key,
      title,
      objective,
      required_themes: splitCsv(themesCsv ?? ""),
      participating_characters: splitCsv(charsCsv ?? ""),
      prerequisites: splitCsv(prereqCsv ?? ""),
      draft_text: null,
    };
  });

  return {
    premise: form.premise.trim(),
    themes,
    characters,
    chapters,
    canon_rules: splitLines(form.canonRulesRaw),
  };
};

export const applyBlueprintToForm = (title: string, blueprint: StoryBlueprint): StoryFormState => ({
  title,
  premise: blueprint.premise,
  canonRulesRaw: blueprint.canon_rules.join("\n"),
  themesRaw: blueprint.themes.map((theme) => `${theme.key}|${theme.statement}|${theme.priority}`).join("\n"),
  charactersRaw: blueprint.characters
    .map((character) => `${character.key}|${character.role}|${character.motivation}`)
    .join("\n"),
  chaptersRaw: blueprint.chapters
    .map((chapter) =>
      [
        chapter.key,
        chapter.title,
        chapter.objective,
        chapter.required_themes.join(","),
        chapter.participating_characters.join(","),
        chapter.prerequisites.join(","),
      ].join("|"),
    )
    .join("\n"),
});
