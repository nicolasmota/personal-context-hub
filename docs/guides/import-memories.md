# Import memories

Bring saved memories from ChatGPT or Claude into the vault. Chat transcripts are not imported. Imported text is `source_imported`, marked untrusted, and does not create a grant.

## ChatGPT

If the account export contains `memory.json`, that file is a JSON array. Each object uses `content` (or `text` / `memory`). Entries with `enabled: false` are skipped.

```bash
uv run personal-context import-memories --data-dir ~/.personal-context --src ~/Downloads/memory.json --provider chatgpt
```

A `.zip` is accepted when it contains `memory.json`. A zip that only has `conversations.json` is refused.

If the export has no memory file, paste the saved-memory list into a text file, one fact per line, and pass `--provider chatgpt`.

## Claude

`memories.json` from Settings → Privacy → Export data. The importer reads:

- `conversations_memory` — one prose block
- `memory_files[]` — `{ "path", "content" }`
- `project_memories` — map of project id to text
- older row objects with `content`, `memory`, or `text`

The same file may be a one-element array. A zip is accepted when `memories.json` is inside it.

```bash
uv run personal-context import-memories --data-dir ~/.personal-context --src ~/Downloads/memories.json --provider claude
```

Running the import again skips statements that are already stored with the same origin label.
