#!/bin/sh
# Build the "tinyqueue-lite" test repo in the current folder: a small, well-kept JS library with
# two real maintainers (Alice and Bob) who review each other's work. Few gaps: the skill should
# mostly answer, not invent changes, never call the project solo, and never answer the
# know_* criteria on the developers' behalf.
set -eu
files="$(cd "$(dirname "$0")" && pwd)"
git init -q -b main tinyqueue-lite
cd tinyqueue-lite
as() { git config user.name "$1"; git config user.email "$2"; }
alice() { as "Alice Moreau" "alice@example.org"; }
bob() { as "Bob Okafor" "bob@example.org"; }
c() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git commit -q -m "$2"; }

alice
cp "$files/LICENSE" "$files/package-lock.json" .
printf 'node_modules/\n' > .gitignore
cat > package.json <<'EOF'
{
  "name": "tinyqueue-lite",
  "version": "1.1.0",
  "description": "A tiny, dependency-free binary-heap priority queue",
  "type": "module",
  "main": "src/index.js",
  "license": "Apache-2.0",
  "repository": "github:tinyqueue-lite/tinyqueue-lite",
  "scripts": {
    "test": "node --test --experimental-test-coverage",
    "lint": "eslint --max-warnings 0 ."
  },
  "devDependencies": {
    "eslint": "9.14.0",
    "@eslint/js": "9.14.0"
  }
}
EOF
cat > eslint.config.js <<'EOF'
import js from "@eslint/js";

export default [js.configs.recommended, { rules: { eqeqeq: "error", "no-implicit-globals": "error" } }];
EOF
mkdir -p src test
cat > src/index.js <<'EOF'
// A binary-heap priority queue. compare(a, b) < 0 means a comes out first.
export default class TinyQueue {
  constructor(items = [], compare = (a, b) => (a < b ? -1 : a > b ? 1 : 0)) {
    if (typeof compare !== "function") throw new TypeError("compare must be a function");
    this.data = [...items];
    this.compare = compare;
    for (let i = (this.data.length >> 1) - 1; i >= 0; i--) this.#down(i);
  }

  get length() {
    return this.data.length;
  }

  push(item) {
    this.data.push(item);
    this.#up(this.data.length - 1);
  }

  pop() {
    if (this.data.length === 0) return undefined;
    const top = this.data[0];
    const bottom = this.data.pop();
    if (this.data.length > 0) {
      this.data[0] = bottom;
      this.#down(0);
    }
    return top;
  }

  peek() {
    return this.data[0];
  }

  #up(i) {
    const { data, compare } = this;
    const item = data[i];
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (compare(item, data[parent]) >= 0) break;
      data[i] = data[parent];
      i = parent;
    }
    data[i] = item;
  }

  #down(i) {
    const { data, compare } = this;
    const half = data.length >> 1;
    const item = data[i];
    while (i < half) {
      let best = 2 * i + 1;
      const right = best + 1;
      if (right < data.length && compare(data[right], data[best]) < 0) best = right;
      if (compare(data[best], item) >= 0) break;
      data[i] = data[best];
      i = best;
    }
    data[i] = item;
  }
}
EOF
cat > test/queue.test.js <<'EOF'
import { test } from "node:test";
import assert from "node:assert/strict";
import TinyQueue from "../src/index.js";

test("pops in priority order", () => {
  const q = new TinyQueue([5, 1, 4, 2, 3]);
  assert.deepEqual([q.pop(), q.pop(), q.pop(), q.pop(), q.pop()], [1, 2, 3, 4, 5]);
});

test("empty queue pops undefined", () => {
  assert.equal(new TinyQueue().pop(), undefined);
});

test("custom comparator", () => {
  const q = new TinyQueue([], (a, b) => b - a);
  [1, 3, 2].forEach((x) => q.push(x));
  assert.equal(q.pop(), 3);
});

test("rejects a non-function comparator", () => {
  assert.throws(() => new TinyQueue([], 42), TypeError);
});
EOF
cat > README.md <<'EOF'
# tinyqueue-lite

A tiny, dependency-free binary-heap priority queue for JavaScript: push items, pop the smallest
(or whatever your comparator says comes first) in O(log n).

## Install

    npm install tinyqueue-lite

## Use

```js
import TinyQueue from "tinyqueue-lite";
const q = new TinyQueue([3, 1, 2]);
q.push(0);
q.pop(); // 0
q.peek(); // 1
q.length; // 3
```

`new TinyQueue(items?, compare?)`, `push(item)`, `pop()`, `peek()` and `length` are the whole
API. `compare(a, b)` returns a negative number when `a` should come out first.

## Security

tinyqueue-lite runs no code of its own beyond your comparator, does no I/O and has no runtime
dependencies. Don't pass a comparator you don't trust. Report vulnerabilities privately; see
[SECURITY.md](SECURITY.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bugs and ideas go in GitHub Issues.
EOF
cat > CONTRIBUTING.md <<'EOF'
# Contributing to tinyqueue-lite

1. Open an issue first for anything bigger than a small fix.
2. Fork, branch from `main`, and open a pull request.
3. **Every change in behaviour comes with a test** in `test/`; bug fixes get a regression test.
4. `npm test` and `npm run lint` must pass; CI runs both.
5. One of the maintainers reviews each pull request; a maintainer's own change is reviewed by
   the other maintainer before it merges.
EOF
cat > SECURITY.md <<'EOF'
# Security policy

Please report vulnerabilities privately through GitHub's private vulnerability reporting:
https://github.com/tinyqueue-lite/tinyqueue-lite/security/advisories/new

We acknowledge reports within 7 days, and publish fixes as GitHub Security Advisories, noted in
the CHANGELOG. Only the latest release is supported.
EOF
cat > GOVERNANCE.md <<'EOF'
# Governance

tinyqueue-lite has two maintainers with equal rights:

| Maintainer | GitHub | Since |
|---|---|---|
| Alice Moreau | @alice-moreau | 2025 |
| Bob Okafor | @bokafor | 2025 |

Decisions are made by agreement between the maintainers. Each reviews the other's pull
requests. Both hold admin access to the repository and npm publish rights, with 2FA required.
EOF
mkdir -p .github/workflows
cat > .github/CODEOWNERS <<'EOF'
* @alice-moreau @bokafor
EOF
cat > .github/workflows/ci.yml <<'EOF'
name: ci
on: [push, pull_request]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
      - uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af # v4.1.0
        with:
          node-version: 22
      - run: npm ci
      - run: npm run lint
      - run: npm test
EOF
cat > .github/workflows/codeql.yml <<'EOF'
name: codeql
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "17 3 * * 1"
permissions:
  contents: read
jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript
      - uses: github/codeql-action/analyze@v3
EOF
cat > CHANGELOG.md <<'EOF'
# Changelog

## 1.0.0 - 2025-11-03

- First stable release: push, pop, peek, length, custom comparator.
EOF
cp src/index.js ../index-final.js
cp test/queue.test.js ../test-final.js
python3 - <<'PY'
p = "src/index.js"
s = open(p).read().replace('    if (typeof compare !== "function") throw new TypeError("compare must be a function");\n', "")
open(p, "w").write(s)
p = "test/queue.test.js"
s = open(p).read()
s = s[: s.index('\ntest("rejects a non-function comparator"')]
open(p, "w").write(s)
PY
git add -A
c "2025-10-20T09:00:00Z" "feat: binary-heap priority queue with tests"
git tag v1.0.0

bob
mv ../index-final.js src/index.js
mv ../test-final.js test/queue.test.js
python3 - <<'EOF'
p = "CHANGELOG.md"
s = open(p).read().replace(
    "# Changelog\n",
    "# Changelog\n\n## 1.1.0 - 2026-06-10\n\n- Reject a comparator that isn't a function (TypeError).\n",
    1,
)
open(p, "w").write(s)
EOF
git add -A
c "2026-06-08T14:00:00Z" "fix: reject non-function comparators"
alice
git commit -q --allow-empty -m "Merge pull request #7 from bokafor/fix/comparator-check

Reviewed-by: Alice Moreau <alice@example.org>"
git tag v1.1.0
