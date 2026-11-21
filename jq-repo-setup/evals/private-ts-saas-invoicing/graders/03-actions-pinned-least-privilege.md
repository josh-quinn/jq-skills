---
type: llm
focus: trace
weight: 1
---

Every third-party 'uses:' in the generated workflows is pinned to a 40-character commit SHA with a version comment, each workflow has top-level 'permissions: contents: read' (broader permissions only at job level where needed), and every actions/checkout sets 'persist-credentials: false'
