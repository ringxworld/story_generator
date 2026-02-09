# Wiki Docs Sync

Long-form docs are authored in-repo under `docs/`, published as a static
snapshot on GitHub Pages under `/docs/`, and mirrored to the GitHub wiki.

## Why this split

- Wiki is easier for repository visitors to browse quickly.
- In-repo docs stay versioned with code and ADRs.
- GitHub Pages can focus on the product demo snapshot.

## Commands

Preview wiki sync locally:

```bash
make wiki-sync
```

Publish synced docs to the live wiki:

```bash
make wiki-sync-push
```

## URLs

- Wiki: `https://github.com/ringxworld/story_generator/wiki`
- Product demo (Pages): `https://ringxworld.github.io/story_generator/`
- Hosted docs (Pages): `https://ringxworld.github.io/story_generator/docs/`
