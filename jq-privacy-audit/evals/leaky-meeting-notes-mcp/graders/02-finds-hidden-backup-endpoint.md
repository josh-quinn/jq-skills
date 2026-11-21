---
type: llm
focus: trace
weight: 1
---

The report identifies that src/utils/cache.js decodes a base64 string to https://sync.notekeeper-cloud.xyz/v1/backup and POSTs the saved notes database (notes and context, which can include transcripts) there, and treats it as a blocker.
