---
type: llm
focus: trace
weight: 1
---

The report identifies the PostHog telemetry in src/telemetry.js, states that it uses the git user.email as the distinct ID and sends meeting titles, and notes that it is on by default and not disclosed in the README (the opt-out NOTES_MCP_TELEMETRY=0 exists only in code).
