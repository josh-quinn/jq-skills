#!/usr/bin/env python3
"""Shared helper for the jq-privacy-audit skills.

Finds the places in a code base where personal data could be read, stored or sent
(network calls, telemetry SDKs, sensitive file reads, hidden URLs, agent instructions),
classifies every host it finds against the user's trust profile, fetches packages
without running them, unpacks Electron app archives, and lists what is installed.

A finding is a lead for a person or an agent to read, never a verdict.

Run it with PyYAML available, e.g.:
    uv run --no-project --with pyyaml python -I privacy.py <command> --help
"""

from __future__ import annotations

import argparse
import base64
import binascii
import bisect
import fnmatch
import gzip
import hashlib
import io
import ipaddress
import json
import os
import re
import socket
import struct
import subprocess
import sys
import tarfile
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

import yaml

TOOL = "privacy-audit"
HERE = Path(__file__).resolve().parent
SIGNATURES = HERE / "signatures.yaml"
STATUS_ORDER = ("flag", "check", "decide", "ok")
DEFAULT_CONFIG = """\
# Settings for the jq-privacy-audit skills (jq-privacy-audit, jq-privacy-sandbox).
# Edit freely: the skills read this file and never rewrite it.

# Where reports, fetched sources and sandbox logs go: <data_dir>/<target>/<date>/
data_dir: ~/development/privacy-audits

# Which trust profile to use: work, personal or auto. auto picks work when this
# computer's name matches one of work_computer_names (shell-style, any case).
# PRIVACY_AUDIT_PROFILE=work|personal overrides it for one run.
profile: auto
work_computer_names: []   # e.g. ["ACME-*", "*-corp-*"]

# A domain covers its subdomains: trusting google.com also trusts analytics.google.com.
profiles:
  personal:
    # Calls to the service a tool exists for (slack.com for a Slack MCP) are fine.
    own_service: trusted
    # Fine for any tool.
    trusted_domains:
      - github.com
      - githubusercontent.com
      - youtube.com
      - googlevideo.com
      - ytimg.com
      - registry.npmjs.org
      - pypi.org
      - files.pythonhosted.org
    # AI model APIs you've decided may receive your data. Empty: every AI provider is
    # flagged for your decision.
    approved_ai_endpoints: []
  work:
    # On the work laptop a tool's own service still needs your (or IT's) OK,
    # unless it is listed in trusted_domains.
    own_service: confirm
    trusted_domains:
      - github.com
      - githubusercontent.com
      - registry.npmjs.org
      - pypi.org
      - files.pythonhosted.org
    approved_ai_endpoints: []

# Extra patterns, merged with the built-in ones (jq-privacy-common/scripts/signatures.yaml):
# signatures:
#   patterns:
#     network-call: {in: [code], regex: ['\\bmyHttpClient\\(']}
#   hosts:
#     telemetry: [metrics.acme-vendor.com]
"""

SKIP_DIRS = {".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox"}
DEP_DIRS = {"node_modules", "bower_components", "vendor", "site-packages", ".venv", "venv"}
MAX_BYTES = 2_000_000
LOCKFILES = {
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "poetry.lock", "uv.lock", "Pipfile.lock", "pdm.lock", "go.sum", "Cargo.lock", "Gemfile.lock",
    "composer.lock",
}
MANIFESTS = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "go.mod", "Cargo.toml",
    "Gemfile", "composer.json", "manifest.json", "plugin.json", "marketplace.json",
}
INSTRUCTION_NAMES = {"SKILL.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "copilot-instructions.md", ".cursorrules"}
INSTRUCTION_DIRS = {"commands", "agents", "prompts", "skills", "rules", ".claude", ".cursor", ".github"}
TEST_DIRS = {"test", "tests", "__tests__", "__mocks__", "spec", "specs", "testdata", "fixtures", "e2e", "smoke"}
# Long lines that are drawing data, not code: inline SVG paths and embedded images.
SVG_DATA_RE = re.compile(r"<svg\b|<path\b|\bd=[\"']M|data:image/")
TEST_FILE_RE = re.compile(r"(^test_.*\.py$|_test\.(py|go)$|\.(test|spec)\.[cm]?[jt]sx?$)")
ASSET_EXT = {".svg", ".css", ".scss", ".sass", ".less", ".map"}
CI_RE = re.compile(r"(^|/)(\.github/workflows|\.circleci|\.buildkite)/|(^|/)(\.gitlab-ci\.yml|azure-pipelines\.yml|"
                   r"bitbucket-pipelines\.yml|\.travis\.yml|Jenkinsfile)$")
WHERE_ORDER = ("runtime", "test", "ci")
DOC_EXT = {".md", ".markdown", ".rst", ".txt", ".adoc", ".mdx"}
CONFIG_EXT = {".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".plist", ".xml"}
URL_RE = re.compile(r"\b(?:https?|wss?)://([A-Za-z0-9._~-]+|\[[0-9a-fA-F:]+\])(?::\d+)?", re.I)
QUOTED_HOST_RE = re.compile(
    r"""["'`]((?:[a-z0-9-]+\.)+(?:com|io|net|org|dev|ai|co|app|sh|xyz|me|cloud|site|info|ru|cn|tk|top|so|gg|link|pro|live|fun))["'`/:]""",
    re.I,
)
B64_RE = re.compile(r"""["'`]([A-Za-z0-9+/_-]{16,}={0,2})["'`]""")


def die(msg: str):
    sys.exit(f"privacy.py: {msg}")


# --- config and profiles ----------------------------------------------------


def config_path() -> Path:
    root = os.environ.get("JQ_TOOLS_CONFIG") or "~/.config/jq-tools"
    return Path(root).expanduser() / TOOL / "config.yaml"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = yaml.safe_load(DEFAULT_CONFIG)
    cfg = {**defaults, **data}
    profiles = {**defaults["profiles"], **(data.get("profiles") or {})}
    cfg["profiles"] = {name: {**defaults["profiles"].get(name, {}), **(p or {})} for name, p in profiles.items()}
    cfg["data_dir"] = str(Path(str(cfg["data_dir"])).expanduser())
    cfg["config_file"] = str(path)
    return cfg


def computer_name() -> str:
    try:
        out = subprocess.run(["scutil", "--get", "ComputerName"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass  # not macOS, or scutil failed: use the hostname instead
    return socket.gethostname()


def resolve_profile(cfg: dict, override: str | None = None) -> tuple[str, str]:
    """The profile to use, and a short note on why."""
    choice = override or os.environ.get("PRIVACY_AUDIT_PROFILE")
    if choice:
        source = "--profile" if override else "PRIVACY_AUDIT_PROFILE"
    else:
        choice, source = str(cfg.get("profile") or "auto"), "config"
    if choice != "auto":
        if choice not in cfg["profiles"]:
            die(f"unknown profile {choice!r}; the config has {', '.join(cfg['profiles'])}")
        return choice, source
    patterns = cfg.get("work_computer_names") or []
    if not patterns:
        return "personal", "auto: no work_computer_names set, so this may be a work laptop"
    name = computer_name()
    for pat in patterns:
        if fnmatch.fnmatch(name.lower(), str(pat).lower()):
            return "work", f"auto: computer name {name!r} matches {pat!r}"
    return "personal", f"auto: computer name {name!r} matches no work_computer_names"


def load_signatures(cfg: dict) -> dict:
    sig = yaml.safe_load(SIGNATURES.read_text(encoding="utf-8"))
    extra = cfg.get("signatures") or {}
    for cat, spec in (extra.get("patterns") or {}).items():
        base = sig["patterns"].setdefault(cat, {"in": spec.get("in", ["code"]), "regex": []})
        base["regex"] = [*base["regex"], *spec.get("regex", [])]
    for kind, hosts in (extra.get("hosts") or {}).items():
        sig["hosts"][kind] = [*sig["hosts"].get(kind, []), *hosts]
    return sig


# --- host classification ----------------------------------------------------


def clean_host(host: str) -> str:
    host = host.strip().lower().rstrip(".")
    if host.startswith("["):
        return host.strip("[]").split("]")[0]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def host_matches(host: str, entry: str) -> bool:
    entry = entry.lower()
    if entry.endswith("."):
        return host.startswith(entry)
    return host == entry or host.endswith("." + entry)


def is_inert_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_unspecified or ip.is_link_local


class Policy:
    """The user's trust profile plus the built-in host lists."""

    def __init__(self, cfg: dict, profile: str, own: list[str] | None = None, source: str = ""):
        self.cfg, self.profile, self.source = cfg, profile, source
        p = cfg["profiles"][profile]
        self.trusted = [str(d) for d in p.get("trusted_domains") or []]
        self.approved_ai = [str(d) for d in p.get("approved_ai_endpoints") or []]
        self.own_ok = str(p.get("own_service", "trusted")) == "trusted"
        self.own = [d.lower() for d in own or []]
        self.lists = load_signatures(cfg)["hosts"]

    def classify(self, host: str) -> tuple[str, str]:
        """(kind, status) for one host. status is ok, decide, check or flag."""
        h = clean_host(host)
        if is_inert_ip(h) or h.endswith((".example", ".test", ".local", ".invalid", ".localhost", ".internal")):
            return "inert", "ok"

        def any_of(entries):
            return any(host_matches(h, e) for e in entries)

        if any_of(self.lists.get("inert", [])):
            return "inert", "ok"
        if any_of(self.lists.get("cdn", [])):
            return "cdn", "ok"
        if any_of(self.approved_ai):
            return "approved-ai", "ok"
        if any_of(self.trusted):
            return "trusted", "ok"
        if any_of(self.own):
            return "own-service", "ok" if self.own_ok else "decide"
        for kind, status in (("exfil-risk", "flag"), ("telemetry", "flag"), ("ai-provider", "decide"),
                             ("model-hub", "ok"), ("cloud-storage", "decide")):
            if any_of(self.lists.get(kind, [])):
                return kind, status
        return "unknown", "check"


# --- scan -------------------------------------------------------------------


def file_kind(rel: Path, in_skill: bool) -> str:
    name = rel.name
    if name in LOCKFILES:
        return "lockfile"
    if name in MANIFESTS or re.fullmatch(r"requirements.*\.txt", name) or name.endswith(".gemspec"):
        return "manifest"
    ext = rel.suffix.lower()
    if name in INSTRUCTION_NAMES or name.endswith((".prompt.md", ".mdc", ".instructions.md")):
        return "instructions"
    if ext in DOC_EXT and name.lower().startswith(("readme", "changelog", "contributing", "license", "security")):
        return "docs"
    if ext in DOC_EXT:
        if in_skill or INSTRUCTION_DIRS & set(rel.parts[:-1]):
            return "instructions"
        return "docs"
    if name.lower().startswith(("license", "licence", "copying", "notice", "changelog")):
        return "docs"
    if ext in ASSET_EXT:
        return "asset"
    if ext in CONFIG_EXT or name.startswith(".env"):
        return "config"
    return "code"


def walk(root: Path, deps: bool):
    """(path, kind) for each file, and the files skipped as (path, reason)."""
    files, skipped = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        keep = []
        for n in sorted(dirnames):
            if n in SKIP_DIRS or (not deps and (n in DEP_DIRS or (d / n / "pyvenv.cfg").exists())):
                if n not in SKIP_DIRS:
                    skipped.append((d / n, "dependency folder (use --deps)"))
                continue
            keep.append(n)
        dirnames[:] = keep
        in_skill = any((p / "SKILL.md").exists() for p in [d, *d.parents] if p == root or root in p.parents)
        for n in sorted(filenames):
            path = d / n
            if path.is_symlink():
                skipped.append((path, f"symlink to {os.readlink(path)}"))
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_BYTES:
                skipped.append((path, f"over {MAX_BYTES // 1_000_000} MB"))
                continue
            with open(path, "rb") as f:
                head = f.read(8192)
            if b"\0" in head:
                skipped.append((path, "binary"))
                continue
            files.append((path, file_kind(path.relative_to(root), in_skill)))
    return files, skipped


def decoded_hosts(line: str) -> list[str]:
    """Hosts hidden in base64 string literals on this line."""
    found = []
    for token in B64_RE.findall(line):
        t = token.replace("-", "+").replace("_", "/")
        try:
            raw = base64.b64decode(t + "=" * (-len(t) % 4), validate=True)
            text = raw.decode("ascii")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
        if text.isprintable():
            found += URL_RE.findall(text)
    return found


def scan(root: Path, policy: Policy, deps: bool = False) -> dict:
    root = Path(root).resolve()
    if not root.exists():
        die(f"{root} does not exist")
    sig = load_signatures(policy.cfg)["patterns"]
    compiled = {cat: (set(spec["in"]), combine(spec["regex"])) for cat, spec in sig.items()}
    findings, hosts = [], {}
    files, skipped = walk(root, deps) if root.is_dir() else ([(root, file_kind(Path(root.name), False))], [])
    base = root if root.is_dir() else root.parent
    for path, kind in files:
        rel = str(path.relative_to(base))
        in_tests = bool(TEST_DIRS & set(Path(rel).parts[:-1])) or bool(TEST_FILE_RE.search(path.name))
        # Where the file runs: findings and hosts in tests and CI matter less than the shipped code's.
        where = "ci" if CI_RE.search(rel) else "test" if in_tests else "runtime"
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")
        starts = [0]
        for line in lines[:-1]:
            starts.append(starts[-1] + len(line) + 1)

        def line_of(offset: int, starts=starts) -> int:  # bound now: this runs inside the loop
            return bisect.bisect_right(starts, offset)

        # Whole-file searches are far faster than line by line; one finding per line and category.
        if kind == "code":
            long = next((i for i, line in enumerate(lines, 1) if len(line) > 1000 and not SVG_DATA_RE.search(line)), None)
            if long:
                findings.append({"category": "obfuscation", "file": rel, "line": long, "kind": kind, "where": where,
                                 "text": f"minified or generated line ({len(lines[long - 1])} chars): read it with care"})
        for cat, (kinds, regex) in compiled.items():
            if kind not in kinds:
                continue
            done = set()
            for m in regex.finditer(text):
                # A match can begin with the newline before the keyword; count from the keyword.
                no = line_of(m.start() + len(m.group(0)) - len(m.group(0).lstrip()))
                if no not in done:
                    done.add(no)
                    findings.append({"category": cat, "file": rel, "line": no, "kind": kind, "where": where,
                                     "text": snippet(lines[no - 1], regex)})
        if kind == "lockfile":
            continue
        # A URL in a manifest is metadata (homepage, author) unless its line runs something.
        runs = ({line_of(m.start() + len(m.group(0)) - len(m.group(0).lstrip())) for m in compiled["network-call"][1].finditer(text)}
                if kind == "manifest" else set())
        refs = [(m.group(1), "url", m.start()) for m in URL_RE.finditer(text)]
        if kind in ("code", "config", "instructions"):
            refs += [(m.group(1), "quoted", m.start()) for m in QUOTED_HOST_RE.finditer(text)]
            refs += [(h, "base64", m.start()) for m in B64_RE.finditer(text) for h in decoded_hosts(m.group(0))]
        seen = set()
        for h, via, offset in refs:
            h, no = clean_host(h), line_of(offset)
            if not h or "." not in h and h != "localhost" or (h, via, no) in seen or bogus_ip(h):
                continue
            seen.add((h, via, no))
            ref_kind = kind
            if kind == "manifest" and no not in runs:
                ref_kind = "metadata"
            elif where != "runtime":
                ref_kind = where
            entry = hosts.setdefault(h, {"host": h, "refs": []})
            entry["refs"].append({"file": rel, "line": no, "kind": ref_kind, "via": via})
    for h in hosts.values():
        h["refs"].sort(key=lambda r: (r["file"], r["line"]))
    for h in hosts.values():
        h["kind"], h["status"] = policy.classify(h["host"])
        h["docs_only"] = all(r["kind"] in ("docs", "metadata", "test", "ci", "asset") for r in h["refs"])
    ordered = sorted(hosts.values(), key=lambda h: (STATUS_ORDER.index(h["status"]), h["docs_only"], h["host"]))
    return {
        "root": str(root),
        "profile": policy.profile,
        "profile_source": policy.source,
        "own_service": policy.own,
        "files_scanned": len(files),
        "skipped": [{"file": str(p.relative_to(base)), "reason": r} for p, r in skipped],
        "hosts": ordered,
        "findings": findings,
    }


def combine(regexes: list[str]) -> re.Pattern:
    """One pattern for a category. A leading (?i) becomes a scoped (?i:...) group."""
    parts = [f"(?i:{r[4:]})" if r.startswith("(?i)") else f"(?:{r})" for r in regexes]
    return re.compile("|".join(parts), re.M)


def bogus_ip(host: str) -> bool:
    """All-numeric labels that aren't a whole IPv4 address, like 127.0.0 from a format string."""
    return bool(re.fullmatch(r"[\d.]+", host)) and not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", host)


def snippet(line: str, regex: re.Pattern) -> str:
    line = line.strip()
    if len(line) <= 160:
        return line
    m = regex.search(line)
    start = max(0, m.start() - 60) if m else 0
    return ("…" if start else "") + line[start:start + 160] + "…"


def format_scan(result: dict, limit: int = 40) -> str:
    """Text summary: every host to flag or decide, the first `limit` of the others, and findings."""
    out = [
        f"Scanned {result['files_scanned']} files in {result['root']}, profile {result['profile']}"
        + (f" ({result['profile_source']})" if result["profile_source"] else ""),
    ]
    if result["own_service"]:
        out.append(f"Own service: {', '.join(result['own_service'])}")
    if result["skipped"]:
        reasons = {}
        for s in result["skipped"]:
            reasons.setdefault(s["reason"], []).append(s["file"])
        out.append("Not scanned: " + "; ".join(f"{len(v)} {k} ({', '.join(v[:3])}{', …' if len(v) > 3 else ''})" for k, v in reasons.items()))
    counts = {s: sum(h["status"] == s for h in result["hosts"]) for s in STATUS_ORDER}
    out.append(f"\nHosts ({len(result['hosts'])}: " + ", ".join(f"{n} {s}" for s, n in counts.items() if n) + "), most worrying first")
    shown = {"check": 0, "ok": 0}
    for h in result["hosts"]:
        if h["status"] in shown:
            shown[h["status"]] += 1
            if shown[h["status"]] > limit:
                continue
        where = ", ".join(f"{r['file']}:{r['line']}" + (f" [{r['via']}]" if r["via"] != "url" else "") for r in h["refs"][:3])
        more = f" +{len(h['refs']) - 3}" if len(h["refs"]) > 3 else ""
        out.append(f"  {h['status']:<6} {h['kind']:<13} {h['host']:<40} {where}{more}{'  (docs, tests or CI only)' if h['docs_only'] else ''}")
    for status, n in shown.items():
        if n > limit:
            out.append(f"  … {n - limit} more {status} hosts (use --json, or --limit)")
    by_cat = {}
    for f in result["findings"]:
        by_cat.setdefault(f["category"], []).append(f)
    out.append(f"\nFindings ({len(result['findings'])})")
    # Shipped code first; leads in tests and CI follow, a few at a time.
    by_cat = dict(sorted(by_cat.items(), key=lambda kv: not any(f["where"] == "runtime" for f in kv[1])))
    for cat, items in by_cat.items():
        runtime = [f for f in items if f["where"] == "runtime"]
        rest = sorted((f for f in items if f["where"] != "runtime"), key=lambda f: WHERE_ORDER.index(f["where"]))
        out.append(f"  {cat} ({len(runtime)} in shipped code" + (f", {len(rest)} in tests or CI)" if rest else ")"))
        for f in runtime[:limit]:
            out.append(f"    {f['file']}:{f['line']}  [{f['kind']}]  {f['text']}")
        if len(runtime) > limit:
            out.append(f"    … {len(runtime) - limit} more (use --json for all)")
        if rest:
            n_test, n_ci = sum(f["where"] == "test" for f in rest), sum(f["where"] == "ci" for f in rest)
            out.append("    + " + ", ".join(x for x in (f"{n_test} in tests" if n_test else "", f"{n_ci} in CI" if n_ci else "") if x) + ":")
            for f in rest[:min(5, limit)]:
                out.append(f"      {f['file']}:{f['line']}  [{f['where']}]  {f['text']}")
            if len(rest) > min(5, limit):
                out.append(f"      … {len(rest) - min(5, limit)} more (use --json for all)")
    return "\n".join(out)


# --- work folder ------------------------------------------------------------


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "target"


def init_work(cfg: dict, target: str) -> dict:
    parent = Path(cfg["data_dir"]) / slug(target)
    previous = sorted(parent.glob("*/report.md")) if parent.exists() else []
    day = date.today().isoformat()
    work, n = parent / day, 2
    while work.exists():
        work, n = parent / f"{day}-{n}", n + 1
    (work / "source").mkdir(parents=True)
    return {"work_dir": str(work), "source_dir": str(work / "source"),
            "previous_report": str(previous[-1]) if previous else None}


# --- fetching without running -----------------------------------------------


def get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "privacy-audit (+source review)", "Accept-Encoding": "gzip"})  # noqa: S310 - https registry URLs only
    with urlopen(req, timeout=60) as r:  # noqa: S310 - https registry URLs only
        data = r.read()
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" and not url.endswith((".tgz", ".tar.gz")) else data


def safe_extract(data: bytes, dest: Path) -> int:
    """Unpack a tar or zip archive into dest: regular files and folders only, never outside dest."""
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    count = 0

    def target(name: str) -> Path | None:
        p = (dest / name).resolve()
        return p if p == dest or dest in p.parents else None

    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                p = target(info.filename)
                if p is None or info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:
                    continue
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(z.read(info))
                count += 1
        return count
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
        for m in tar.getmembers():
            p = target(m.name)
            if p is None or not m.isfile():
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(tar.extractfile(m).read())
            count += 1
    return count


def fetch(kind: str, spec: str, dest: Path) -> dict:
    """Download a package's published files and unpack them. Nothing is installed or run."""
    if kind == "npm":
        name, _, version = spec[1:].partition("@") if spec.startswith("@") else spec.partition("@")
        name = "@" + name if spec.startswith("@") else name
        meta = json.loads(get(f"https://registry.npmjs.org/{quote(name, safe='@')}"))
        version = version or meta["dist-tags"]["latest"]
        dist = meta["versions"][version]["dist"]
        data = get(dist["tarball"])
        algo, _, digest = dist.get("integrity", "").partition("-")
        if algo == "sha512" and base64.b64encode(hashlib.sha512(data).digest()).decode() != digest:
            die("npm tarball does not match its published integrity hash")
        url = dist["tarball"]
    elif kind == "pypi":
        name, _, version = spec.partition("==")
        meta = json.loads(get(f"https://pypi.org/pypi/{name}/{version + '/' if version else ''}json"))
        files = meta["urls"]
        pick = next((f for f in files if f["packagetype"] == "sdist"), None) or next(iter(files), None)
        if not pick:
            die(f"no files published for {spec}")
        data = get(pick["url"])
        if hashlib.sha256(data).hexdigest() != pick["digests"]["sha256"]:
            die("PyPI file does not match its published sha256")
        version, url = meta["info"]["version"], pick["url"]
    elif kind == "vsix":
        pub, _, ext = spec.partition(".")
        try:
            meta = json.loads(get(f"https://open-vsx.org/api/{pub}/{ext}"))
            url, version = meta["files"]["download"], meta["version"]
        except Exception:  # noqa: BLE001 - not on Open VSX: use the Microsoft marketplace
            version = "latest"
            url = f"https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{pub}/vsextensions/{ext}/latest/vspackage"
        data = get(url)
    else:
        die(f"unknown kind {kind!r}; use npm, pypi or vsix (clone git repos with git)")
    count = safe_extract(data, dest)
    return {"kind": kind, "name": spec, "version": version, "url": url, "files": count, "dest": str(dest)}


def unasar(archive: Path, dest: Path) -> int:
    """Unpack an Electron app.asar without Node. Files marked unpacked live in app.asar.unpacked/."""
    dest = Path(dest).resolve()
    with open(archive, "rb") as f:
        _, header_size = struct.unpack("<II", f.read(8))
        _, json_len = struct.unpack("<II", f.read(8))
        header = json.loads(f.read(json_len))
        base = 8 + header_size
        count = 0

        def walk_node(node: dict, prefix: Path):
            nonlocal count
            for name, child in node.get("files", {}).items():
                p = (dest / prefix / name).resolve()
                if dest not in p.parents:
                    die(f"{archive} has a path outside the archive: {prefix / name}")
                if "files" in child:
                    walk_node(child, prefix / name)
                elif "link" in child or child.get("unpacked"):
                    continue
                else:
                    f.seek(base + int(child["offset"]))
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(f.read(int(child["size"])))
                    count += 1

        walk_node(header, Path("."))
    return count


# --- inventory --------------------------------------------------------------


SECRET_RE = re.compile(r"^(xox[a-z]-|sk-|ghp_|gho_|ghs_|github_pat_|glpat-|AKIA|eyJ|ntn_|secret_)|^[A-Za-z0-9_\-]{32,}$")
SECRET_FLAG_RE = re.compile(r"(?i)(token|key|secret|password|passwd|auth|bearer|cookie)")


def mask_args(args: list) -> list[str]:
    out, hide_next = [], False
    for a in map(str, args):
        if hide_next or SECRET_RE.search(a):
            out.append("***")
        elif "=" in a and SECRET_FLAG_RE.search(a.split("=", 1)[0]):
            out.append(a.split("=", 1)[0] + "=***")
        else:
            out.append(a)
        hide_next = a.startswith("-") and bool(SECRET_FLAG_RE.search(a)) and "=" not in a
    return out


def mcp_item(name: str, spec: dict, where: str) -> dict:
    url = spec.get("url") or spec.get("serverUrl")
    return {
        "kind": "mcp",
        "name": name,
        "where": where,
        "transport": spec.get("type") or ("http" if url else "stdio"),
        "command": " ".join(mask_args([spec.get("command", ""), *spec.get("args", [])])).strip() or None,
        "url": urlsplit(url)._replace(query="", fragment="").geturl() if url else None,
        "env_keys": sorted((spec.get("env") or {}).keys()),
        "header_keys": sorted((spec.get("headers") or {}).keys()),
    }


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def inventory(home: Path) -> list[dict]:
    """Skills, plugins, hooks, MCP servers and editor/browser extensions installed for this user."""
    home = Path(home)
    items = []
    for d in (".claude/skills", ".copilot/skills", ".agents/skills", ".codex/skills"):
        for p in sorted((home / d).glob("*/SKILL.md")):
            items.append({"kind": "skill", "name": p.parent.name, "where": str(p.parent), "path": str(p.parent.resolve())})
    for p in sorted((home / ".claude/plugins").glob("cache/*/*/*")) + sorted((home / ".claude/plugins").glob("marketplaces/*")):
        if p.is_dir():
            cached = "cache" in p.parts
            items.append({"kind": "plugin" if cached else "plugin-marketplace",
                          "name": f"{p.parent.name}@{p.parent.parent.name}" if cached else p.name, "where": "~/.claude/plugins", "path": str(p)})
    claude = read_json(home / ".claude.json") or {}
    for name, spec in (claude.get("mcpServers") or {}).items():
        items.append(mcp_item(name, spec, "~/.claude.json (user)"))
    for proj, conf in (claude.get("projects") or {}).items():
        for name, spec in (conf.get("mcpServers") or {}).items():
            items.append(mcp_item(name, spec, f"~/.claude.json (project {proj})"))
    for rel in ("Library/Application Support/Claude/claude_desktop_config.json", ".cursor/mcp.json",
                ".config/Code/User/mcp.json", "Library/Application Support/Code/User/mcp.json"):
        conf = read_json(home / rel) or {}
        for name, spec in (conf.get("mcpServers") or conf.get("servers") or {}).items():
            items.append(mcp_item(name, spec, "~/" + rel))
    codex = home / ".codex/config.toml"
    if codex.exists():
        import tomllib

        try:
            for name, spec in (tomllib.loads(codex.read_text()).get("mcp_servers") or {}).items():
                items.append(mcp_item(name, spec, "~/.codex/config.toml"))
        except tomllib.TOMLDecodeError:
            pass  # a broken Codex config is skipped, not fatal to the inventory
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        hooks = (read_json(home / rel) or {}).get("hooks") or {}
        for event, groups in hooks.items():
            for g in groups or []:
                for h in g.get("hooks", []):
                    items.append({"kind": "hook", "name": event, "where": "~/" + rel,
                                  "command": " ".join(mask_args(str(h.get("command", "")).split()))})
    for d in (".vscode/extensions", ".cursor/extensions", ".windsurf/extensions"):
        for p in sorted((home / d).glob("*/package.json")):
            items.append({"kind": "editor-extension", "name": p.parent.name, "where": "~/" + d, "path": str(p.parent)})
    chrome = home / "Library/Application Support/Google/Chrome"
    for m in sorted(chrome.glob("*/Extensions/*/*/manifest.json")):
        meta = read_json(m) or {}
        items.append({"kind": "browser-extension", "name": str(meta.get("name", m.parts[-3])), "id": m.parts[-3],
                      "where": f"Chrome {m.parts[-5]}", "path": str(m.parent)})
    return items


def format_inventory(items: list[dict]) -> str:
    out = []
    for kind in ("skill", "plugin", "plugin-marketplace", "hook", "mcp", "editor-extension", "browser-extension"):
        group = [i for i in items if i["kind"] == kind]
        if not group:
            continue
        out.append(f"{kind} ({len(group)})")
        for i in group:
            detail = i.get("url") or i.get("command") or i.get("path") or ""
            extra = f"  env: {', '.join(i['env_keys'])}" if i.get("env_keys") else ""
            out.append(f"  {i['name']:<32} {detail}{extra}   [{i['where']}]")
    return "\n".join(out) or "nothing found"


# --- cli --------------------------------------------------------------------


def make_policy(args, cfg: dict) -> Policy:
    profile, source = resolve_profile(cfg, getattr(args, "profile", None))
    own = [d.strip() for d in (getattr(args, "own", None) or "").split(",") if d.strip()]
    return Policy(cfg, profile, own=own, source=source)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="privacy.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("config", help="print the resolved config and profile")

    p = sub.add_parser("init", help="make a work folder for one audit")
    p.add_argument("--target", required=True, help="name of what is being audited")

    for name, help_ in (("scan", "list candidate data flows and hosts"), ("classify", "classify hosts")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--profile", choices=("work", "personal"))
        p.add_argument("--own", help="comma-separated domains of the service the tool exists for")
        if name == "scan":
            p.add_argument("path", type=Path)
            p.add_argument("--deps", action="store_true", help="also scan node_modules, vendor and virtualenvs")
            p.add_argument("--json", action="store_true")
            p.add_argument("--limit", type=int, default=40, help="findings shown per category")
        else:
            p.add_argument("hosts", nargs="+")

    p = sub.add_parser("fetch", help="download a package's files without installing or running it")
    p.add_argument("kind", choices=("npm", "pypi", "vsix"))
    p.add_argument("spec", help="name, name@version (npm), name==version (pypi), publisher.extension (vsix)")
    p.add_argument("dest", type=Path)

    p = sub.add_parser("unasar", help="unpack an Electron app.asar")
    p.add_argument("archive", type=Path)
    p.add_argument("dest", type=Path)

    p = sub.add_parser("inventory", help="list installed skills, plugins, hooks, MCP servers, extensions")
    p.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    cfg = load_config()
    if args.cmd == "config":
        profile, source = resolve_profile(cfg)
        print(yaml.safe_dump({"config_file": cfg["config_file"], "data_dir": cfg["data_dir"],
                              "profile": profile, "profile_source": source,
                              "rules": cfg["profiles"][profile]}, sort_keys=False).rstrip())
    elif args.cmd == "init":
        print(json.dumps(init_work(cfg, args.target), indent=2))
    elif args.cmd == "scan":
        result = scan(args.path, make_policy(args, cfg), deps=args.deps)
        print(json.dumps(result, indent=2) if args.json else format_scan(result, args.limit))
    elif args.cmd == "classify":
        pol = make_policy(args, cfg)
        print(f"profile {pol.profile} ({pol.source})")
        for h in args.hosts:
            kind, status = pol.classify(h)
            print(f"  {status:<6} {kind:<13} {h}")
    elif args.cmd == "fetch":
        print(json.dumps(fetch(args.kind, args.spec, args.dest), indent=2))
    elif args.cmd == "unasar":
        print(f"unpacked {unasar(args.archive, args.dest)} files to {args.dest}")
    elif args.cmd == "inventory":
        items = inventory(Path.home())
        print(json.dumps(items, indent=2) if args.json else format_inventory(items))


if __name__ == "__main__":
    main()
