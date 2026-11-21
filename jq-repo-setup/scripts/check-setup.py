#!/usr/bin/env python3
"""Check that a repository still has what jq-repo-setup (and the OpenSSF badge skills) set up.

Reads .github/repo-setup.yaml, the record those skills leave in the repo, and runs quick checks
that need no judgement: files, hooks, workflows, pinning, dependency updates, lockfiles, secrets,
GitHub settings and the badge level. It changes nothing.

    uv run --no-project --with pyyaml python -I check-setup.py [repo] [--offline] [--json]

Exit status: 0 all checks pass (warnings allowed), 1 something failed, 2 no setup record.
--offline skips the checks that need GitHub or bestpractices.dev.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

NOTE = ".github/repo-setup.yaml"
REQUIRED = {
    "skill": None,
    "date": None,
    "visibility": ("public", "private"),
    "project_type": ("tool", "library", "app", "saas-b2b"),
    "team": ("solo", "team"),
}
SITE = "https://www.bestpractices.dev"
LEVELS = ["in_progress", "passing", "silver", "gold"]
LEVEL_PERCENT = {"passing": "badge_percentage_0", "silver": "badge_percentage_1",
                 "gold": "badge_percentage_2"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^\s'\"#]+)", re.M)
PLACEHOLDER_RE = re.compile(r"<[A-Z][A-Z0-9_-]{2,}>|\b[\w.+-]+@example\.(?:com|org)\b")
# The one accepted exception to SHA pinning: SLSA's generator must be referenced by tag.
UNPINNED_OK = ("slsa-framework/slsa-github-generator/",)
LOCKFILES = {
    "package.json": ("package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock",
                     "bun.lock", "bun.lockb"),
    "pyproject.toml": ("uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock", "requirements.txt"),
    "Cargo.toml": ("Cargo.lock",),
    "Gemfile": ("Gemfile.lock",),
    "composer.json": ("composer.lock",),
    "go.mod": ("go.sum",),
}


@dataclass
class Check:
    id: str
    status: str  # pass | fail | warn | skip
    detail: str


def load_note(repo: Path) -> tuple[dict | None, list[str]]:
    """The setup record, and what's wrong with it (missing or invalid fields)."""
    p = repo / NOTE
    if not p.is_file():
        return None, [f"no {NOTE}"]
    try:
        note = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return None, [f"{NOTE} isn't valid YAML: {e}"]
    if not isinstance(note, dict):
        return None, [f"{NOTE} isn't a mapping"]
    setup = note.get("setup") or {}
    problems = []
    for key, allowed in REQUIRED.items():
        val = setup.get(key)
        if val in (None, ""):
            problems.append(f"setup.{key} is missing")
        elif allowed and val not in allowed:
            problems.append(f"setup.{key} is {val!r}, not one of {', '.join(allowed)}")
    return note, problems


def _exists(repo: Path, *names: str) -> bool:
    return any((repo / n).exists() for n in names)


def _workflows(repo: Path) -> list[Path]:
    d = repo / ".github" / "workflows"
    return sorted(p for p in d.glob("*.y*ml")) if d.is_dir() else []


def _load_yaml(p: Path):
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None


def check_foundations(repo: Path, public: bool) -> Check:
    wanted = {
        "README.md": ("README.md", "README"),
        "CONTRIBUTING.md": ("CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"),
        "SECURITY.md": ("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"),
        "CHANGELOG.md": ("CHANGELOG.md", "CHANGELOG"),
        ".gitignore": (".gitignore",),
        "AGENTS.md or CLAUDE.md": ("AGENTS.md", "CLAUDE.md"),
        "docs/adr/": ("docs/adr", "docs/decisions", "adr"),
    }
    if public:
        wanted["LICENSE"] = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
        wanted["CODE_OF_CONDUCT.md"] = ("CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md",
                                        "docs/CODE_OF_CONDUCT.md")
    missing = [name for name, alts in wanted.items() if not _exists(repo, *alts)]
    if missing:
        return Check("foundations", "fail", "missing: " + ", ".join(missing))
    return Check("foundations", "pass", f"{len(wanted)} files present")


def check_placeholders(repo: Path) -> Check:
    files = [*repo.glob("*.md"), *repo.glob("SECURITY-INSIGHTS.y*ml"), *repo.glob("docs/**/*.md"),
             *repo.glob(".github/**/*.md"), *repo.glob(".github/**/*.y*ml"),
             *repo.glob(".github/CODEOWNERS")]
    hits = []
    for p in sorted(set(files)):
        if p.name == "template.md" or not p.is_file():
            continue
        found = sorted(set(PLACEHOLDER_RE.findall(p.read_text(encoding="utf-8", errors="replace"))))
        if found:
            hits.append(f"{p.relative_to(repo)} ({', '.join(found[:3])})")
    if hits:
        return Check("placeholders", "fail", "template placeholders left in: " + "; ".join(hits))
    return Check("placeholders", "pass", "none found")


def check_hooks(repo: Path) -> Check:
    if (repo / ".pre-commit-config.yaml").is_file():
        return Check("hooks", "pass", "pre-commit framework config present")
    hooks = repo / ".githooks"
    missing = [h for h in ("commit-msg", "pre-push") if not (hooks / h).is_file()]
    if missing:
        return Check("hooks", "fail", "missing .githooks/" + ", .githooks/".join(missing))
    not_exec = [h for h in ("commit-msg", "pre-push") if not (hooks / h).stat().st_mode & 0o111]
    if not_exec:
        return Check("hooks", "fail", "not executable: " + ", ".join(not_exec))
    r = subprocess.run(["git", "-C", str(repo), "config", "core.hooksPath"],
                       capture_output=True, text=True)
    if r.stdout.strip() != ".githooks":
        return Check("hooks", "warn", "hooks exist but aren't enabled in this clone "
                     "(git config core.hooksPath .githooks, usually `make hooks`)")
    return Check("hooks", "pass", "commit-msg and pre-push enabled")


def check_target(repo: Path) -> Check:
    for name in ("Makefile", "makefile", "GNUmakefile", "justfile", "Justfile"):
        p = repo / name
        if p.is_file() and re.search(r"^check\b[^\n=]*:", p.read_text(errors="replace"), re.M):
            return Check("check-target", "pass", f"`check` in {name}")
        if p.is_file() and name.lower() == "justfile" and re.search(r"^check\b", p.read_text(), re.M):
            return Check("check-target", "pass", f"`check` in {name}")
    pkg = repo / "package.json"
    if pkg.is_file():
        try:
            if "check" in (json.loads(pkg.read_text()).get("scripts") or {}):
                return Check("check-target", "pass", "`check` script in package.json")
        except (json.JSONDecodeError, AttributeError):
            pass
    return Check("check-target", "fail", "no `check` target (Makefile, justfile or package.json) "
                 "that runs what CI runs")


def _triggers(doc) -> set[str]:
    on = doc.get("on", doc.get(True)) if isinstance(doc, dict) else None  # YAML 1.1 reads on: as True
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    if isinstance(on, dict):
        return set(on)
    return set()


def check_ci(repo: Path) -> Check:
    wfs = _workflows(repo)
    if not wfs:
        return Check("ci", "fail", "no workflows in .github/workflows")
    on_pr = [p.name for p in wfs if "pull_request" in _triggers(_load_yaml(p))]
    if not on_pr:
        return Check("ci", "fail", "no workflow runs on pull_request")
    return Check("ci", "pass", "runs on pull requests: " + ", ".join(on_pr))


def check_workflow_permissions(repo: Path) -> Check:
    wfs = _workflows(repo)
    if not wfs:
        return Check("workflow-permissions", "skip", "no workflows")
    bad = [p.name for p in wfs if not (isinstance(d := _load_yaml(p), dict) and "permissions" in d)]
    if bad:
        return Check("workflow-permissions", "fail", "no top-level permissions: " + ", ".join(bad))
    return Check("workflow-permissions", "pass", f"{len(wfs)} workflows set top-level permissions")


def check_actions_pinned(repo: Path) -> Check:
    wfs = _workflows(repo) + sorted(repo.glob(".github/actions/**/action.y*ml"))
    if not wfs:
        return Check("actions-pinned", "skip", "no workflows")
    bad = []
    for p in wfs:
        for ref in USES_RE.findall(p.read_text(encoding="utf-8", errors="replace")):
            if ref.startswith(("./", "docker://")) or ref.startswith(UNPINNED_OK):
                continue
            if not SHA_RE.match(ref.rpartition("@")[2]):
                bad.append(f"{p.name}: {ref}")
    if bad:
        return Check("actions-pinned", "fail", "not pinned to a commit SHA: " + "; ".join(bad))
    return Check("actions-pinned", "pass", "every action is SHA-pinned")


def check_dependency_updates(repo: Path) -> Check:
    if _exists(repo, "renovate.json", "renovate.json5", ".renovaterc", ".renovaterc.json",
               ".github/renovate.json", ".github/renovate.json5"):
        return Check("dependency-updates", "pass", "Renovate config present")
    for name in (".github/dependabot.yml", ".github/dependabot.yaml"):
        doc = _load_yaml(repo / name) if (repo / name).is_file() else None
        if doc is not None:
            ecosystems = {u.get("package-ecosystem") for u in (doc.get("updates") or [])
                          if isinstance(u, dict)}
            if _workflows(repo) and "github-actions" not in ecosystems:
                return Check("dependency-updates", "fail",
                             f"{name} doesn't update github-actions")
            return Check("dependency-updates", "pass", "Dependabot: " + ", ".join(sorted(ecosystems)))
    return Check("dependency-updates", "fail", "no Dependabot or Renovate config")


def check_lockfile(repo: Path) -> Check:
    missing, seen = [], []
    for manifest, locks in LOCKFILES.items():
        m = repo / manifest
        if not m.is_file():
            continue
        if manifest == "go.mod" and "require" not in m.read_text(errors="replace"):
            continue  # no dependencies, no go.sum
        seen.append(manifest)
        if not _exists(repo, *locks):
            missing.append(f"{manifest} (expected one of {', '.join(locks)})")
    if not seen:
        return Check("lockfile", "skip", "no dependency manifest at the top level")
    if missing:
        return Check("lockfile", "fail", "no lockfile for " + "; ".join(missing))
    return Check("lockfile", "pass", "lockfile committed for " + ", ".join(seen))


def check_secrets(repo: Path, gitleaks: str | None) -> Check:
    if not gitleaks:
        return Check("secrets", "skip", "gitleaks isn't installed")
    r = subprocess.run([gitleaks, "git", "--no-banner", "--redact", "-l", "error", str(repo)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return Check("secrets", "pass", "gitleaks found nothing in the history")
    if r.returncode == 1:
        return Check("secrets", "fail", "gitleaks found possible secrets: run "
                     f"`gitleaks git {repo}` to see them")
    return Check("secrets", "warn", f"gitleaks couldn't run: {(r.stderr or r.stdout).strip()[:200]}")


def _github_slug(repo: Path) -> str | None:
    r = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", r.stdout.strip())
    return f"{m[1]}/{m[2]}" if m else None


def check_github_settings(repo: Path, public: bool, gh) -> Check:
    slug = _github_slug(repo)
    if not slug:
        return Check("github-settings", "skip", "no GitHub remote")
    info = gh(f"repos/{slug}")
    if not isinstance(info, dict):
        return Check("github-settings", "skip", f"can't read {slug} (is gh logged in?)")
    branch = info.get("default_branch") or "main"
    problems = []
    rules = gh(f"repos/{slug}/rules/branches/{branch}")
    protection = None if rules else gh(f"repos/{slug}/branches/{branch}/protection")
    if not rules and not protection:
        problems.append(f"no ruleset or branch protection on {branch}")
    ssa = info.get("security_and_analysis") or {}
    if public and (ssa.get("secret_scanning") or {}).get("status") != "enabled":
        problems.append("secret scanning is off")
    if public:
        pvr = gh(f"repos/{slug}/private-vulnerability-reporting")
        if not (isinstance(pvr, dict) and pvr.get("enabled")):
            problems.append("private vulnerability reporting is off")
    if problems:
        return Check("github-settings", "fail", f"{slug}: " + "; ".join(problems))
    return Check("github-settings", "pass", f"{slug}: {branch} protected"
                 + ("; secret scanning and private vulnerability reporting on" if public else ""))


def check_openssf_badge(repo: Path, note: dict | None, fetch) -> Check:
    rec = ((note or {}).get("badges") or {}).get("openssf") or {}
    pid, level = rec.get("project_id"), rec.get("level")
    if not pid:
        return Check("openssf-badge", "skip", "no OpenSSF badge recorded")
    if fetch is None:
        return Check("openssf-badge", "skip", "offline")
    try:
        site = fetch(f"{SITE}/projects/{pid}.json")
    except Exception as e:  # noqa: BLE001 - any network failure is a warning, not a crash
        return Check("openssf-badge", "warn", f"couldn't reach {SITE}: {e}")
    now = (site or {}).get("badge_level", "in_progress")
    below = now not in LEVELS or (level in LEVELS and LEVELS.index(now) < LEVELS.index(level))
    if below:
        pct = (site or {}).get(LEVEL_PERCENT.get(level, ""), "?")
        return Check("openssf-badge", "fail",
                     f"project {pid} is {now} on {SITE}, recorded as {level} ({level} at {pct}%)")
    readme = next((p for p in (repo / "README.md", repo / "README") if p.is_file()), None)
    if not readme or not re.search(rf"bestpractices\.(?:dev|coreinfrastructure\.org)/(?:\w+/)?projects/{pid}\b",
                                   readme.read_text(errors="replace")):
        return Check("openssf-badge", "warn", f"{now} on the site, but the README doesn't show "
                     f"the badge for project {pid}")
    return Check("openssf-badge", "pass", f"project {pid}: {now}")


def _fetch(url: str):
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "check-setup"})
    with urlopen(req, timeout=15) as r:  # noqa: S310 - fixed https URL
        return json.load(r)


def _gh(path: str):
    if not shutil.which("gh"):
        return None
    try:
        r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def run_checks(repo: Path, offline: bool = False, fetch=_fetch, gh=_gh,
               gitleaks: str | None | bool = True) -> list[Check]:
    """Run every check. gitleaks=True looks the tool up on PATH; None or False skips it."""
    repo = Path(repo).resolve()
    if gitleaks is True:
        gitleaks = shutil.which("gitleaks")
    note, problems = load_note(repo)
    public = ((note or {}).get("setup") or {}).get("visibility", "public") != "private"
    checks = [
        Check("note", "fail" if problems else "pass", "; ".join(problems) or f"{NOTE} is complete"),
        check_foundations(repo, public),
        check_placeholders(repo),
        check_hooks(repo),
        check_target(repo),
        check_ci(repo),
        check_workflow_permissions(repo),
        check_actions_pinned(repo),
        check_dependency_updates(repo),
        check_lockfile(repo),
        check_secrets(repo, gitleaks),
    ]
    if offline:
        checks.append(Check("github-settings", "skip", "offline"))
        checks.append(check_openssf_badge(repo, note, None))
    else:
        checks.append(check_github_settings(repo, public, gh))
        checks.append(check_openssf_badge(repo, note, fetch))
    return checks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--offline", action="store_true", help="skip GitHub and bestpractices.dev")
    ap.add_argument("--json", action="store_true", help="print the results as JSON")
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()
    note, _ = load_note(repo)
    checks = run_checks(repo, offline=args.offline)
    failed = [c.id for c in checks if c.status == "fail"]
    warned = [c.id for c in checks if c.status == "warn"]
    if args.json:
        print(json.dumps({"repo": str(repo), "setup": (note or {}).get("setup"),
                          "checks": [asdict(c) for c in checks],
                          "failed": failed, "warnings": warned}, indent=2, default=str))
    else:
        s = (note or {}).get("setup") or {}
        head = (f"recorded {s.get('date')}: {s.get('visibility')} {s.get('project_type')}, "
                f"{s.get('team')}") if note else f"no setup record ({NOTE})"
        print(f"repo-setup check for {repo.name} ({head})")
        for c in checks:
            print(f"  {c.status.upper():4} {c.id:21} {c.detail}")
        counts = {k: sum(c.status == k for c in checks) for k in ("fail", "warn", "pass", "skip")}
        print(f"{counts['fail']} failed, {counts['warn']} warnings, {counts['pass']} passed, "
              f"{counts['skip']} skipped")
    if note is None:
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
