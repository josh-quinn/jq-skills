# notes-mcp

Search, summarise and annotate your meeting transcripts from Claude, Cursor or any MCP client.

**Private by design: your notes never leave your machine.** Transcripts are read from your
recordings folder and indexed locally in `~/.notes-mcp/`.

## Setup

```json
{ "mcpServers": { "notes": { "command": "npx", "args": ["-y", "notes-mcp"],
  "env": { "NOTES_DIR": "~/Meetings", "OPENAI_API_KEY": "sk-..." } } } }
```

Summaries use your own OpenAI key (`OPENAI_API_KEY`). Leave it unset to disable summaries.

## Tools

- `list_meetings`, `get_transcript`, `summarize_meeting`, `save_note`
