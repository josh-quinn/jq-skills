#!/usr/bin/env python3
"""Shared helper for the openssf-* badge skills.

Reads the OpenSSF Best Practices criteria live from upstream, keeps a per-project
work folder, drafts the gap table, checks an answers file against the criteria's
rules, and builds bestpractices.dev "automation proposal" URLs from it.

Run it with PyYAML available, e.g.:
    uv run --no-project --with pyyaml python -I badge.py <command> --help
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import yaml

TOOL = "openssf-badge-skills"
SITE = "https://www.bestpractices.dev"
UPSTREAM = "ossf/best-practices-badge"
FILES = [
    "criteria/criteria.yml",
    "config/locales/en.yml",
    "criteria/baseline_criteria.yml",
    "criteria/metal_to_baseline_map.yml",
]
METAL = {"passing": "0", "silver": "1", "gold": "2"}
BASELINE = ("baseline-1", "baseline-2", "baseline-3")
LEVELS = (*METAL, *BASELINE)
STATUSES = ("Met", "Unmet", "N/A", "?")
CATEGORIES = ("MUST", "SHOULD", "SUGGESTED")
# Statements about a person, which only that person can make.
PERSONAL = {"know_secure_design", "know_common_errors"}
URL_RE = re.compile(r"https?://\S+")
DEFAULT_CONFIG = """\
# Settings for the openssf-* badge skills (openssf-passing, -silver, -gold, -baseline).
# Edit freely: the skills read this file and never rewrite it.

# Where each project's gap tables, answers files and criteria snapshots are kept,
# as <data_dir>/<project>/<level>/.
data_dir: ~/development/openssf-badges

# Longest proposal URL to build before splitting the answers over several URLs.
max_url_length: 6000
"""


# --- criteria -------------------------------------------------------------


class _Loader(yaml.SafeLoader):
    """SafeLoader that reads upstream's !!omap blocks as plain (ordered) dicts."""


def _omap(loader, node):
    out = {}
    for item in node.value:
        for k, v in item.value:
            out[loader.construct_object(k, deep=True)] = loader.construct_object(v, deep=True)
    return out


_Loader.add_constructor("tag:yaml.org,2002:omap", _omap)


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Loader)  # noqa: S506 - a SafeLoader subclass


def plain(text) -> str:
    text = re.sub(r"<[^>]+>", "", str(text or ""))
    return " ".join(html.unescape(text).split())


def _walk(node: dict, path: list[str]):
    for key, value in node.items():
        if not isinstance(value, dict):
            continue
        if "category" in value:
            yield path, key, value
        else:
            yield from _walk(value, [*path, str(key)])


def load_criteria(criteria_dir: Path, level: str) -> list[dict]:
    """The live criteria of one level, in form order, without obsolete or future ones."""
    if level not in LEVELS:
        sys.exit(f"unknown level {level!r}; expected one of {', '.join(LEVELS)}")
    criteria_dir = Path(criteria_dir)
    if level in METAL:
        level_id = METAL[level]
        tree = load_yaml(criteria_dir / "criteria.yml")[level_id]
    else:
        level_id = level
        tree = load_yaml(criteria_dir / "baseline_criteria.yml")[level]
    en_path = criteria_dir / "en.yml"
    en = (load_yaml(en_path)["en"]["criteria"].get(level_id) or {}) if en_path.exists() else {}
    items = []
    for path, key, c in _walk(tree, []):
        if c.get("obsolete") or c.get("future"):
            continue
        text = en.get(key) or {}
        items.append(
            {
                "key": key,
                "level": level,
                "group": " / ".join(path),
                "category": c["category"],
                "na_allowed": bool(c.get("na_allowed")),
                "na_justification_required": bool(c.get("na_justification_required")),
                "met_url_required": bool(c.get("met_url_required")),
                "met_justification_required": bool(c.get("met_justification_required")),
                "description": plain(text.get("description") or c.get("description")),
                "details": plain(text.get("details") or c.get("details")),
                "original_id": c.get("original_id"),
            }
        )
    return items


def flags(c: dict) -> str:
    return ("N" if c["na_allowed"] else "") + ("U" if c["met_url_required"] else "") + (
        "J" if c["met_justification_required"] else ""
    )


# --- config and work folder -----------------------------------------------


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
    cfg["data_dir"] = str(Path(str(cfg["data_dir"])).expanduser())
    cfg["config_file"] = str(path)
    return cfg


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", name.strip().lower()).strip("-") or "project"


def _get(url: str, timeout: int = 30) -> bytes:
    req = Request(url, headers={"User-Agent": f"{TOOL} (badge helper)", "Accept": "*/*"})  # noqa: S310
    with urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed https hosts
        return r.read()


def fetch_criteria(dest: Path, ref: str | None = None) -> dict:
    """Download the criteria files at one upstream commit, so the snapshot is consistent."""
    if not ref:
        try:
            ref = json.loads(_get(f"https://api.github.com/repos/{UPSTREAM}/commits/main", 15))["sha"]
        except Exception:  # noqa: BLE001 - rate limits etc.; fall back to the branch
            ref = "main"
    dest.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        (dest / Path(f).name).write_bytes(_get(f"https://raw.githubusercontent.com/{UPSTREAM}/{ref}/{f}"))
    return {"repo": UPSTREAM, "ref": ref, "fetched_at": _now()}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_url(url: str) -> str:
    url = url.strip().lower().rstrip("/")
    return url[:-4] if url.endswith(".git") else url


def find_project(repo_url: str) -> dict | None:
    """The bestpractices.dev entry for a repository URL, or None if it is not registered."""
    data = json.loads(_get(f"{SITE}/en/projects.json?url={quote(repo_url, safe='')}"))
    want = _norm_url(repo_url)
    for p in data if isinstance(data, list) else []:
        if _norm_url(p.get("repo_url") or "") == want or _norm_url(p.get("homepage_url") or "") == want:
            return p
    return None


def get_project(project_id: int) -> dict:
    return json.loads(_get(f"{SITE}/projects/{int(project_id)}.json"))


def project_summary(p: dict) -> dict:
    keys = ["id", "name", "repo_url", "badge_level"] + [k for k in p if k.startswith("badge_percentage_")]
    return {k: p.get(k) for k in keys}


def init_workdir(project, level, repo_url=None, criteria_from=None, lookup=True, ref=None) -> dict:
    cfg = load_config()
    work = Path(cfg["data_dir"]) / slug(project) / level
    crit = work / "criteria"
    crit.mkdir(parents=True, exist_ok=True)
    if criteria_from:
        for f in FILES:
            src = Path(criteria_from) / Path(f).name
            if src.exists():
                shutil.copyfile(src, crit / src.name)
        source = {"from": str(criteria_from), "fetched_at": _now()}
    else:
        source = fetch_criteria(crit, ref)
    source["level"] = level
    (work / "source.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")

    site = None
    if lookup and repo_url:
        site = find_project(repo_url)
        if site:
            site = get_project(site["id"])  # the full entry, with every answer
            (work / "project.json").write_text(json.dumps(site, indent=2) + "\n", encoding="utf-8")
    elif (work / "project.json").exists():
        site = json.loads((work / "project.json").read_text(encoding="utf-8"))

    items = load_criteria(crit, level)
    gaps = work / "gaps.md"
    if not gaps.exists():
        gaps.write_text(render_gaps(items, level, site, source, project), encoding="utf-8")
    counts = Counter(c["category"] for c in items)
    return {
        "workdir": str(work),
        "criteria_dir": str(crit),
        "source": source,
        "criteria": {k: counts.get(k, 0) for k in CATEGORIES},
        "project": project_summary(site) if site else None,
        "gaps": str(gaps),
        "answers": str(work / "answers.yaml"),
        "config_file": cfg["config_file"],
    }


# --- gap table ------------------------------------------------------------


def _osps_id(key: str) -> str | None:
    m = re.fullmatch(r"osps_([a-z]{2})_(\d\d)_(\d\d)", key)
    return f"OSPS-{m[1].upper()}-{m[2]}.{m[3]}" if m else None


def site_answer(project: dict | None, key: str) -> tuple[str, str]:
    """(status, justification) saved on the site; baseline readbacks use the OSPS id."""
    if not project:
        return "?", ""
    for k in (key, _osps_id(key)):
        if k and f"{k}_status" in project:
            status = project.get(f"{k}_status")
            status = status if status in STATUSES else "?"
            return status, (project.get(f"{k}_justification") or "").strip()
    return "?", ""


def render_gaps(items, level, project=None, source=None, name=None) -> str:
    source = source or {}
    counts = Counter(c["category"] for c in items)
    title = f"# {level} gap table" + (f": {name}" if name else "")
    where = source.get("ref") or source.get("from") or "unknown"
    lines = [
        title,
        "",
        f"Criteria: {UPSTREAM} at {where}, fetched {source.get('fetched_at', '?')}. "
        f"{len(items)} criteria: " + ", ".join(f"{counts.get(k, 0)} {k}" for k in CATEGORIES) + ".",
        "",
        "- Flags: N = N/A allowed, U = Met needs a URL in the justification, J = Met needs a justification.",
        "- On site: the answer saved on bestpractices.dev now (? = none, or no project yet).",
        "- Proposed: Met, Fix (needs a repo change), Unmet (accepted; SHOULD/SUGGESTED only), N/A,",
        "  or Ask (only the user can answer).",
    ]
    group = None
    for c in items:
        if c["group"] != group:
            group = c["group"]
            lines += [
                "",
                f"## {group}",
                "",
                "| Criterion | Cat | Flags | On site | Proposed | Evidence, or what is missing | Requirement |",
                "|---|---|---|---|---|---|---|",
            ]
        status, _ = site_answer(project, c["key"])
        req = c["description"].replace("|", "/")
        req = req if len(req) <= 110 else req[:107] + "..."
        lines.append(f"| {c['key']} | {c['category']} | {flags(c)} | {status} |  |  | {req} |")
    return "\n".join(lines) + "\n"


# --- answers check --------------------------------------------------------


def check_answers(items: list[dict], doc: dict) -> dict:
    answers = (doc or {}).get("answers") or {}
    by_key = {c["key"]: c for c in items}
    level = items[0]["level"] if items else "?"
    errors, warnings, blocking = [], [], []
    summary = {k: Counter() for k in CATEGORIES}

    for key in answers:
        if key not in by_key:
            errors.append(f"{key}: not a current {level} criterion (typo, or obsolete?)")

    for c in items:
        key, cat = c["key"], c["category"]
        a = answers.get(key)
        if a is None:
            errors.append(f"{key}: missing; answer every criterion (status '?' if it truly can't be known yet)")
            if cat == "MUST":
                blocking.append(key)
            continue
        status = str(a.get("status", "")).strip()
        just = str(a.get("justification") or "").strip()
        if status not in STATUSES:
            errors.append(f"{key}: status {status!r} is not one of {', '.join(STATUSES)}")
            continue
        summary[cat][status] += 1
        before = len(errors)

        if status == "N/A":
            if not c["na_allowed"]:
                errors.append(f"{key}: N/A is not an option for this criterion on the form; answer Met or Unmet")
            elif c["na_justification_required"] and not just:
                errors.append(f"{key}: N/A needs a justification here")
        if status == "Met":
            if c["met_url_required"] and not URL_RE.search(just):
                errors.append(f"{key}: Met needs a URL in the justification, or the site says 'not enough for a badge'")
            if c["met_justification_required"] and not just:
                errors.append(f"{key}: Met needs a justification here")
            if not str(a.get("evidence") or "").strip():
                errors.append(f"{key}: Met without evidence; record what you checked (file, setting, CI job, output)")
        if status == "Unmet" and not just:
            if cat == "SHOULD":
                errors.append(f"{key}: a SHOULD left Unmet needs a justification saying why")
            else:
                warnings.append(f"{key}: Unmet with no justification")
        if key in PERSONAL and status in ("Met", "Unmet") and a.get("asked_user") is not True:
            errors.append(f"{key}: a statement about the person; ask the user, then set asked_user: true")
        if status == "?":
            warnings.append(f"{key}: still unknown (?)")
        elif status != "Unmet" and not just and len(errors) == before:
            warnings.append(f"{key}: {status} with no justification")

        if cat == "MUST" and status not in ("Met", "N/A"):
            blocking.append(key)

    return {
        "level": level,
        "criteria": len(items),
        "errors": errors,
        "warnings": warnings,
        "blocking": blocking,
        "summary": {k: dict(v) for k, v in summary.items()},
    }


# --- proposal URLs --------------------------------------------------------


def proposal_urls(doc, level=None, project_id=None, repo_url=None, project=None, max_length=6000) -> list[str]:
    """bestpractices.dev edit URLs that propose these answers for a person to review and save.

    Answers already on the site unchanged are left out. Changed ones are forced with
    `overrides`, because unforced proposals only fill blank fields. Status '?' is never
    proposed: in a URL it resets the field.
    """
    level = level or doc.get("level")
    if level not in LEVELS:
        sys.exit(f"unknown level {level!r}")
    if project_id:
        base, fixed = f"{SITE}/en/projects/{int(project_id)}/{level}/edit", []
    elif repo_url:
        base, fixed = f"{SITE}/en/projects", [("as", "edit"), ("url", repo_url), ("section", level)]
    else:
        sys.exit("need a project id or the repository URL")

    entries = []  # (pairs, forced key or None)
    for key, a in (doc.get("answers") or {}).items():
        status = str(a.get("status", "")).strip()
        if status not in STATUSES or status == "?":
            continue
        just = str(a.get("justification") or "").strip()
        forced = None
        if project is not None:
            cur_status, cur_just = site_answer(project, key)
            if cur_status == status and cur_just == just:
                continue
            if cur_status != "?":
                forced = f"{key}_status"
        entries.append(([(f"{key}_status", status), (f"{key}_justification", just)], forced))

    def build(chunk):
        pairs = list(fixed)
        for p, _ in chunk:
            pairs += p
        forced = [f for _, f in chunk if f]
        if forced:
            pairs.append(("overrides", ",".join(forced)))
        return f"{base}?{urlencode(pairs)}"

    urls, chunk = [], []
    for entry in entries:
        if chunk and len(build([*chunk, entry])) > max_length:
            urls.append(build(chunk))
            chunk = []
        chunk.append(entry)
    if chunk:
        urls.append(build(chunk))
    return urls


def payload(doc, keys=None) -> dict:
    """{key: [status, justification]} for the fill-form.js fallback."""
    out = {}
    for key, a in (doc.get("answers") or {}).items():
        status = str(a.get("status", "")).strip()
        if status in STATUSES and status != "?" and (not keys or key in keys):
            out[key] = [status, str(a.get("justification") or "").strip()]
    return out


# --- CLI ------------------------------------------------------------------


def _load_doc(path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _criteria_dir(args) -> Path:
    if args.criteria:
        return Path(args.criteria)
    return Path(args.answers).resolve().parent / "criteria" if getattr(args, "answers", None) else Path("criteria")


def _print_check(result, path):
    print(f"{path}: {result['criteria']} {result['level']} criteria")
    for cat, counts in result["summary"].items():
        if counts:
            print(f"  {cat}: " + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())))
    for title, rows in (("Errors", result["errors"]), ("Warnings", result["warnings"])):
        if rows:
            print(f"{title} ({len(rows)}):")
            for r in rows:
                print(f"  - {r}")
    if result["blocking"]:
        print(f"MUSTs not Met or N/A ({len(result['blocking'])}), so no badge yet: " + ", ".join(result["blocking"]))
    if result["errors"]:
        print("Result: fix the errors above before proposing these answers.")
    elif result["blocking"]:
        print("Result: the answers are well-formed, but the badge is blocked by the MUSTs above.")
    else:
        print("Result: ready to propose; every MUST is Met or N/A.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="badge.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("config", help="show the settings (creates the config file on first run)")

    p = sub.add_parser("init", help="create the work folder, snapshot the live criteria, look up the project")
    p.add_argument("--project", required=True, help="short project name, used for the folder")
    p.add_argument("--level", required=True, choices=LEVELS)
    p.add_argument("--repo-url", help="the repository URL, to find the project on bestpractices.dev")
    p.add_argument("--ref", help="upstream commit or branch to read the criteria from (default: main now)")
    p.add_argument("--criteria-from", help="copy criteria files from this folder instead of fetching")
    p.add_argument("--no-lookup", action="store_true", help="don't contact bestpractices.dev")

    p = sub.add_parser("list", help="list a level's criteria with their flags")
    p.add_argument("--criteria", required=True, help="folder holding the criteria snapshot")
    p.add_argument("--level", required=True, choices=LEVELS)
    p.add_argument("--details", action="store_true", help="include the details text")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("gaps", help="print a fresh gap table skeleton")
    p.add_argument("--criteria", required=True)
    p.add_argument("--level", required=True, choices=LEVELS)
    p.add_argument("--project-json", help="the project's saved answers (project.json)")

    p = sub.add_parser("check", help="check an answers file against the criteria rules")
    p.add_argument("answers")
    p.add_argument("--criteria", help="criteria folder (default: criteria/ beside the answers file)")
    p.add_argument("--level", choices=LEVELS, help="default: the answers file's level")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("urls", help="build proposal URLs from an answers file")
    p.add_argument("answers")
    p.add_argument("--level", choices=LEVELS)
    p.add_argument("--project-json", help="current answers on the site (default: project.json beside answers)")
    p.add_argument("--project-id", type=int)
    p.add_argument("--repo-url")
    p.add_argument("--max-length", type=int)
    p.add_argument("--out", help="write the URLs here, one per line (default: proposals.txt beside answers)")

    p = sub.add_parser("payload", help="JSON for the fill-form.js fallback")
    p.add_argument("answers")
    p.add_argument("--keys", help="comma-separated subset of criteria")

    p = sub.add_parser("project", help="fetch a project's saved answers from bestpractices.dev")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--id", type=int)
    g.add_argument("--repo-url")
    p.add_argument("--out", help="write the full JSON here")

    args = ap.parse_args(argv)

    if args.cmd == "config":
        print(json.dumps(load_config(), indent=2))
    elif args.cmd == "init":
        out = init_workdir(
            args.project, args.level, args.repo_url, args.criteria_from, lookup=not args.no_lookup, ref=args.ref
        )
        print(json.dumps(out, indent=2))
    elif args.cmd == "list":
        items = load_criteria(Path(args.criteria), args.level)
        if args.json:
            print(json.dumps(items, indent=2))
        for c in [] if args.json else items:
            print(f"{c['category'][:4]} {c['key']} [{flags(c)}] {c['description']}")
            if args.details and c["details"]:
                print(f"      details: {c['details']}")
    elif args.cmd == "gaps":
        site = json.loads(Path(args.project_json).read_text()) if args.project_json else None
        print(render_gaps(load_criteria(Path(args.criteria), args.level), args.level, site), end="")
    elif args.cmd == "check":
        doc = _load_doc(args.answers)
        level = args.level or doc.get("level")
        result = check_answers(load_criteria(_criteria_dir(args), level), doc)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            _print_check(result, args.answers)
        return 1 if result["errors"] else 0
    elif args.cmd == "urls":
        doc = _load_doc(args.answers)
        here = Path(args.answers).resolve().parent
        pj = Path(args.project_json) if args.project_json else here / "project.json"
        site = json.loads(pj.read_text()) if pj.exists() else None
        pid = args.project_id or (site or {}).get("id")
        repo = args.repo_url or doc.get("repo_url")
        max_len = args.max_length or int(load_config().get("max_url_length") or 6000)
        urls = proposal_urls(doc, args.level, pid, repo, site, max_len)
        out = Path(args.out) if args.out else here / "proposals.txt"
        out.write_text("".join(u + "\n" for u in urls), encoding="utf-8")
        print(f"{len(urls)} URL(s) written to {out} (longest {max((len(u) for u in urls), default=0)} chars)")
        if site is None:
            print("No project.json: every answer is proposed unforced, which only fills blank fields.")
    elif args.cmd == "payload":
        keys = set(args.keys.split(",")) if args.keys else None
        print(json.dumps(payload(_load_doc(args.answers), keys), ensure_ascii=False))
    elif args.cmd == "project":
        site = get_project(args.id) if args.id else find_project(args.repo_url)
        if site and not args.id:
            site = get_project(site["id"])
        if not site:
            print("not registered on bestpractices.dev")
            return 3
        if args.out:
            Path(args.out).write_text(json.dumps(site, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(project_summary(site), indent=2))
    return 0


def cli(argv=None) -> int:
    """main(), treating a reader that closed the pipe early (`| head`) as success."""
    try:
        return main(argv)
    except BrokenPipeError:
        # Point stdout at devnull so the interpreter's final flush doesn't fail again.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    sys.exit(cli())
