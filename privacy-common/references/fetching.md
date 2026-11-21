# Getting the code without running it

The audit reads the exact code the user would run. Fetch it into `<work dir>/source/`
(from `privacy.py init`), treat it as untrusted data, and never execute anything from it.

Installing is running: `npm install`, `pip install`, `uvx`, `npx`, `brew install`,
`cargo install` and `go install` all run code from the package (install scripts, build
backends, `setup.py`). So does opening a folder in an editor that trusts its tasks.

| Target | How to get it | Notes |
|---|---|---|
| Git repository | `git clone --depth 1 --no-recurse-submodules <url> source/<name>` | Note the commit (`git -C … rev-parse HEAD`). Submodules are separate code: list them and clone the ones that ship. |
| npm package | `privacy.py fetch npm <name>[@version] source/<name>` | What npm installs, checked against the registry's integrity hash. Usually built JavaScript, sometimes minified: look for a source map or the repository. |
| PyPI package | `privacy.py fetch pypi <name>[==version] source/<name>` | Prefers the source archive; checked against PyPI's sha256. |
| VS Code extension | already installed: `~/.vscode/extensions/<id>-<version>/`; otherwise `privacy.py fetch vsix <publisher>.<name> source/<name>` | The `.vsix` is a zip; the code is under `extension/`. |
| Cursor, Windsurf extensions | `~/.cursor/extensions/`, `~/.windsurf/extensions/` | Same layout as VS Code. |
| Chrome extension | installed: `~/Library/Application Support/Google/Chrome/<profile>/Extensions/<id>/<version>/` | Copy the folder; `privacy.py inventory` lists IDs and names. |
| Electron app | `privacy.py unasar "/Applications/<App>.app/Contents/Resources/app.asar" source/<name>` | Also read `app.asar.unpacked/` beside it (native modules) and `Info.plist`. |
| Claude skill or plugin | copy the folder (from `~/.claude/skills/`, `~/.claude/plugins/cache/…`, or a clone) | Include hooks, `.mcp.json` and every script it calls. |
| MCP server | from its package (npm/PyPI) or repository, at the version the config pins | `privacy.py inventory` shows the command and arguments the user's config runs. |
| Homebrew formula | `brew cat <formula>` (reads the formula, installs nothing) | The formula says where the source or binary comes from; audit that. |
| Binary only | not auditable from source | Say so. `strings -n 8 <binary> \| grep -E 'https?://'` finds embedded hosts; codesign entitlements (`codesign -d --entitlements - <App>.app`) say what it may access. Offer the sandbox, or a network monitor the user runs (LuLu, Little Snitch). |

## Version matters

Audit the version the user will run. A config that runs `npx -y some-mcp@latest` or an
unpinned `uvx some-mcp` fetches whatever is newest at every start, so the audit covers
only today's version; say so and suggest pinning.

## Source and what ships can differ

A GitHub repository is not proof of what's in the published package or binary. When
both exist, audit the package (that's what runs) and use the repository to understand
it. If the package contains code the repository doesn't, that is a finding.

## Running helper scripts near untrusted code

Run your own helpers with `python -I` (isolated mode) and pass the target's path as an
argument, so a planted `json.py` or `yaml.py` in the target can't be imported.
