import { FormEvent, useMemo, useState } from "react";

import { apiBaseUrl, createStory, listStories, login, me, register, updateStory } from "./api";
import { applyBlueprintToForm, buildBlueprintFromForm, emptyStoryForm, StoryFormState } from "./blueprint_form";
import type { StoryResponse } from "./types";

const TOKEN_STORAGE_KEY = "story_gen.token";

const App = (): JSX.Element => {
  const [token, setToken] = useState<string>(() => window.localStorage.getItem(TOKEN_STORAGE_KEY) ?? "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [status, setStatus] = useState("Ready.");
  const [stories, setStories] = useState<StoryResponse[]>([]);
  const [selectedStoryId, setSelectedStoryId] = useState<string | null>(null);
  const [form, setForm] = useState<StoryFormState>(emptyStoryForm);

  const isAuthenticated = token.trim().length > 0;
  const selectedStory = useMemo(
    () => stories.find((story) => story.story_id === selectedStoryId) ?? null,
    [selectedStoryId, stories],
  );

  const refreshStories = async (currentToken: string): Promise<void> => {
    const freshStories = await listStories(currentToken);
    setStories(freshStories);
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
      setStatus(`Signed in as ${user.display_name}.`);
    } catch (error) {
      setStatus(`Login failed: ${(error as Error).message}`);
    }
  };

  const onSignOut = (): void => {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken("");
    setStories([]);
    setSelectedStoryId(null);
    setForm(emptyStoryForm());
    setStatus("Signed out.");
  };

  const onCreateOrUpdate = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!isAuthenticated) {
      setStatus("Sign in before saving stories.");
      return;
    }
    try {
      const blueprint = buildBlueprintFromForm(form);
      if (selectedStory) {
        await updateStory(token, selectedStory.story_id, form.title.trim(), blueprint);
        setStatus(`Updated story: ${form.title}`);
      } else {
        const created = await createStory(token, form.title.trim(), blueprint);
        setSelectedStoryId(created.story_id);
        setStatus(`Created story: ${created.title}`);
      }
      await refreshStories(token);
    } catch (error) {
      setStatus(`Save failed: ${(error as Error).message}`);
    }
  };

  const onSelectStory = (story: StoryResponse): void => {
    setSelectedStoryId(story.story_id);
    setForm(applyBlueprintToForm(story.title, story.blueprint));
  };

  return (
    <main className="shell">
      <header className="hero">
        <h1>story_gen studio</h1>
        <p>
          Build story blueprints with typed contracts, then route them to generation pipelines later.
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
                setForm(emptyStoryForm());
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

          <form onSubmit={onCreateOrUpdate} className="stack">
            <label>
              Title
              <input
                value={form.title}
                onChange={(event) => setForm((state) => ({ ...state, title: event.target.value }))}
              />
            </label>
            <label>
              Premise
              <textarea
                rows={4}
                value={form.premise}
                onChange={(event) => setForm((state) => ({ ...state, premise: event.target.value }))}
              />
            </label>
            <label>
              Canon rules (one per line)
              <textarea
                rows={4}
                value={form.canonRulesRaw}
                onChange={(event) => setForm((state) => ({ ...state, canonRulesRaw: event.target.value }))}
              />
            </label>
            <label>
              Themes (`key|statement|priority`)
              <textarea
                rows={4}
                value={form.themesRaw}
                onChange={(event) => setForm((state) => ({ ...state, themesRaw: event.target.value }))}
              />
            </label>
            <label>
              Characters (`key|role|motivation`)
              <textarea
                rows={4}
                value={form.charactersRaw}
                onChange={(event) => setForm((state) => ({ ...state, charactersRaw: event.target.value }))}
              />
            </label>
            <label>
              Chapters (`key|title|objective|required_themes_csv|characters_csv|prerequisites_csv`)
              <textarea
                rows={5}
                value={form.chaptersRaw}
                onChange={(event) => setForm((state) => ({ ...state, chaptersRaw: event.target.value }))}
              />
            </label>
            <button type="submit">{selectedStory ? "Update Story" : "Create Story"}</button>
          </form>
        </div>
      </section>
    </main>
  );
};

export default App;
