import { FormEvent, useMemo, useState } from "react";

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
import { applyBlueprintToForm, buildBlueprintFromForm, emptyStoryForm, StoryFormState } from "./blueprint_form";
import type { EssayBlueprint, EssayEvaluationResponse, EssayResponse, StoryResponse } from "./types";

const TOKEN_STORAGE_KEY = "story_gen.token";

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

const App = (): JSX.Element => {
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

  const isAuthenticated = token.trim().length > 0;
  const selectedStory = useMemo(
    () => stories.find((story) => story.story_id === selectedStoryId) ?? null,
    [selectedStoryId, stories],
  );
  const selectedEssay = useMemo(
    () => essays.find((essay) => essay.essay_id === selectedEssayId) ?? null,
    [selectedEssayId, essays],
  );

  const refreshStories = async (currentToken: string): Promise<void> => {
    const freshStories = await listStories(currentToken);
    setStories(freshStories);
  };

  const refreshEssays = async (currentToken: string): Promise<void> => {
    const freshEssays = await listEssays(currentToken);
    setEssays(freshEssays);
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

  const onSelectStory = (story: StoryResponse): void => {
    setSelectedStoryId(story.story_id);
    setStoryForm(applyBlueprintToForm(story.title, story.blueprint));
  };

  const onSelectEssay = (essay: EssayResponse): void => {
    setSelectedEssayId(essay.essay_id);
    setEssayTitle(essay.title);
    setEssayDraftText(essay.draft_text);
    setEssayBlueprintRaw(JSON.stringify(essay.blueprint, null, 2));
    setEssayEvaluation(null);
  };

  return (
    <main className="shell">
      <header className="hero">
        <h1>story_gen studio</h1>
        <p>
          Build strict contracts for story and essay generation workflows.
          API base: <code>{apiBaseUrl}</code>
        </p>
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
                setSelectedStoryId(null);
                setStoryForm(emptyStoryForm());
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
