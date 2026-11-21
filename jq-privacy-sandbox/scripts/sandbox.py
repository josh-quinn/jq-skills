#!/usr/bin/env python3
"""Run a tool in a Docker sandbox with planted fake data, and report where it tried to
send things.

    sandbox.py prepare --work <audit work dir> --target <dir> | --package npm:<name> ...
    sandbox.py run <sandbox dir>        # needs the user's go-ahead: it runs the target's code
    sandbox.py report <sandbox dir>
    sandbox.py clean <sandbox dir>

The target sits on a network with no route out. Its only exit is a logging proxy that
forwards allowed hosts and blocks everything else, and never forwards a request that
carries a canary. A watcher logs any attempt to go around the proxy.

Run it with PyYAML available, e.g.:
    uv run --no-project --with pyyaml python -I sandbox.py <command> --help
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import secrets
import shlex
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
sys.path.insert(0, str(HERE.parent.parent / "jq-privacy-common" / "scripts"))
import privacy  # noqa: E402

REGISTRIES = ["registry.npmjs.org", "registry.yarnpkg.com", "pypi.org", "files.pythonhosted.org"]
MODES = ("block", "registries", "trusted")
# Fake credentials, each with the service it belongs to: sending one there is expected use;
# sending it anywhere else is theft.
CREDENTIALS = {
    "SLACK_BOT_TOKEN": ("xoxb-", ["slack.com"]),
    "OPENAI_API_KEY": ("sk-proj-", ["openai.com"]),
    "ANTHROPIC_API_KEY": ("sk-ant-api03-", ["anthropic.com"]),
    "GITHUB_TOKEN": ("ghp_", ["github.com"]),
    "NOTION_TOKEN": ("ntn_", ["notion.com", "notion.so"]),
    "AWS_SECRET_ACCESS_KEY": ("", ["amazonaws.com"]),
}
# Fake personal data: none of it should leave the machine unless that's the tool's job.
DATA_FILES = {
    "ssh-key": (".ssh/id_ed25519", "-----BEGIN OPENSSH PRIVATE KEY-----\n{v}\n-----END OPENSSH PRIVATE KEY-----\n"),
    "aws-credentials": (".aws/credentials", "[default]\naws_access_key_id = AKIA{v}\naws_secret_access_key = {v}\n"),
    "shell-history": (".zsh_history", ": 1731900000:0;export DB_PASSWORD={v}\n: 1731900010:0;git push\n"),
    "meeting-notes": ("Documents/meeting-notes/2026-11-18-standup.md",
                      "# Standup 18 Nov\n\nSam: the acquisition of Northwind closes Friday, codename {v}.\n"),
    "agent-history": (".claude/history.jsonl", '{{"display": "summarise my 1:1 with Priya about her pay rise {v}"}}\n'),
    "git-email": (".gitconfig", "[user]\n  name = Sam Rivera\n  email = sam.{v}@example.com\n"),
    "browser-cookies": (".config/google-chrome/Default/Cookies", "session={v}\n"),
}


def token() -> str:
    return "cnry" + secrets.token_hex(10)


# --- prepare ----------------------------------------------------------------


def detect(target: Path) -> str:
    if (target / "package.json").exists():
        return "node"
    if (target / "pyproject.toml").exists() or (target / "setup.py").exists():
        return "python"
    return "generic"


def default_install(kind: str, package: str | None) -> str:
    if package:
        eco, _, spec = package.partition(":")
        if eco == "npm":
            return f"npm init -y >/dev/null && npm install --no-audit --no-fund {shlex.quote(spec)}"
        if eco == "pypi":
            return f"pip install --no-cache-dir {shlex.quote(spec)}"
        privacy.die(f"--package takes npm:<name> or pypi:<name>, not {package!r}")
    return {"node": "npm install --no-audit --no-fund", "python": "pip install --no-cache-dir .", "generic": "true"}[kind]


def allow_list(mode: str, policy: privacy.Policy, extra: list[str]) -> list[str]:
    if mode == "block":
        return sorted(set(extra))
    allow = set(REGISTRIES) | set(extra)
    if mode == "trusted":
        allow |= set(policy.trusted) | set(policy.own)
    return sorted(allow)


def prepare(args) -> Path:
    work = Path(args.work).expanduser().resolve()
    n = 1
    while (work / f"sandbox-{n}").exists():
        n += 1
    box = work / f"sandbox-{n}"
    for d in ("sandbox", "home", "logs", "ca", "empty"):
        (box / d).mkdir(parents=True)
    target = Path(args.target).expanduser().resolve() if args.target else box / "empty"
    if not target.is_dir():
        privacy.die(f"{target} is not a folder")
    kind = args.kind or (detect(target) if args.target else "generic")

    cfg = privacy.load_config()
    profile, source = privacy.resolve_profile(cfg, args.profile)
    own = [d.strip() for d in (args.own or "").split(",") if d.strip()]
    policy = privacy.Policy(cfg, profile, own=own, source=source)
    extra = [d.strip() for d in (args.allow or "").split(",") if d.strip()]
    allow = allow_list(args.mode, policy, extra)

    canaries, meta, env = {}, {}, {}
    for var, (prefix, services) in CREDENTIALS.items():
        value = prefix + token()
        canaries[f"env:{var}"] = value
        meta[f"env:{var}"] = {"type": "credential", "expected": services}
        env[var] = value
    for cid, (rel, body) in DATA_FILES.items():
        value = token()
        canaries[f"file:{cid}"] = value
        meta[f"file:{cid}"] = {"type": "data", "file": "~/" + rel}
        p = box / "home" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body.format(v=value))
    text = token()
    canaries["input:text"] = text
    meta["input:text"] = {"type": "data", "file": "text given to the tool (MCP arguments, stdin)"}

    ca = "/ca/mitmproxy-ca-cert.pem"
    env.update({
        "HOME": "/root",
        "HTTP_PROXY": "http://proxy:8080", "HTTPS_PROXY": "http://proxy:8080",
        "http_proxy": "http://proxy:8080", "https_proxy": "http://proxy:8080", "NO_PROXY": "", "no_proxy": "",
        "NODE_EXTRA_CA_CERTS": ca, "NODE_USE_ENV_PROXY": "1", "REQUESTS_CA_BUNDLE": ca, "SSL_CERT_FILE": ca,
        "CURL_CA_BUNDLE": ca, "PIP_CERT": ca, "npm_config_cafile": ca, "GIT_SSL_CAINFO": ca,
        "SANDBOX_CANARY_TEXT": f"Please file this: our Q3 board pack says {text}",
    })
    (box / "sandbox" / "target.env").write_text("".join(f"{k}={v}\n" for k, v in env.items()))
    (box / "sandbox" / "canaries.json").write_text(json.dumps(canaries, indent=2))
    (box / "canary-meta.json").write_text(json.dumps(meta, indent=2))

    install = args.install if args.install is not None else default_install(kind, args.package)
    if args.mcp:
        calls = args.calls or "list"
        if calls not in ("list", "auto"):
            shutil.copy(calls, box / "sandbox" / "calls.json")
            calls = "/sandbox/calls.json"
        run = f"python3 /sandbox/mcp_drive.py --calls {calls} --out /logs --timeout 30 -- {args.mcp}"
    else:
        run = args.run or "true"
    (box / "sandbox" / "install.sh").write_text(install + "\n")
    (box / "sandbox" / "run-target.sh").write_text(run + "\n")
    (box / "sandbox" / "run.sh").write_text(f"""\
# Written by sandbox.py prepare.
cp -R /target/. /work/ 2>/dev/null
cd /work
{{ echo "== install: $(cat /sandbox/install.sh)"; timeout {args.timeout} sh /sandbox/install.sh; echo "== exit $?"; }} > /logs/install.log 2>&1
{{ echo "== run: $(cat /sandbox/run-target.sh)"; echo "$SANDBOX_CANARY_TEXT" | timeout {args.timeout} sh /sandbox/run-target.sh; echo "== exit $?"; }} > /logs/run.log 2>&1
sleep {args.linger}
""")
    for f in ("addon.py", "mcp_drive.py"):
        shutil.copy(ASSETS / f, box / "sandbox" / f)
    shutil.copy(ASSETS / "Dockerfile", box / "Dockerfile")
    project = "privacy-sandbox-" + privacy.slug(work.parent.name)[:30] + f"-{n}"
    compose = Template((ASSETS / "compose.yaml.tmpl").read_text()).substitute(
        project=project, allow=",".join(allow), target=str(target))
    (box / "compose.yaml").write_text(compose)
    (box / "settings.json").write_text(json.dumps({
        "target": str(target), "package": args.package, "kind": kind, "mode": args.mode, "allow": allow,
        "profile": profile, "own": own, "install": install, "run": run, "timeout": args.timeout,
    }, indent=2))
    return box


# --- run --------------------------------------------------------------------


def compose(box: Path, *cmd: str, timeout: int | None = None) -> int:
    full = ["docker", "compose", "-f", str(box / "compose.yaml"), *cmd]
    try:
        return subprocess.run(full, cwd=box, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"sandbox: gave up after {timeout}s", file=sys.stderr)
        return 124


def run(box: Path) -> int:
    settings = json.loads((box / "settings.json").read_text())
    budget = 2 * int(settings["timeout"]) + 180
    try:
        return compose(box, "up", "--build", "--exit-code-from", "target", timeout=budget)
    finally:
        compose(box, "down", "--remove-orphans", "--timeout", "2", timeout=120)


# --- report -----------------------------------------------------------------


def read_pcap(path: Path) -> list[tuple]:
    """Bypass attempts in a tcpdump capture, as (kind, value) pairs: ("dns", name) for DNS
    queries, ("syn", "ip:port") for TCP connection attempts, ("arp", ip) for direct sends."""
    if not path.exists() or path.stat().st_size < 24:
        return []
    data = path.read_bytes()
    endian = "<" if data[:4] in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1") else ">"
    linktype = struct.unpack(endian + "I", data[20:24])[0]
    out, pos = [], 24
    while pos + 16 <= len(data):
        incl = struct.unpack(endian + "I", data[pos + 8:pos + 12])[0]
        pkt, pos = data[pos + 16:pos + 16 + incl], pos + 16 + incl
        if linktype == 113:  # Linux cooked capture
            proto, payload = struct.unpack(">H", pkt[14:16])[0], pkt[16:]
        elif linktype == 276:  # Linux cooked capture v2
            proto, payload = struct.unpack(">H", pkt[0:2])[0], pkt[20:]
        elif linktype == 1:  # Ethernet
            proto, payload = struct.unpack(">H", pkt[12:14])[0], pkt[14:]
        else:
            continue
        try:
            out += parse_packet(proto, payload)
        except (struct.error, IndexError, ValueError):
            continue
    return out


def parse_packet(proto: int, p: bytes) -> list[tuple]:
    if proto == 0x0806:  # ARP request "who has <ip>": a direct send to an outside address
        ip = ipaddress.ip_address(p[24:28])
        return [("arp", str(ip))] if p[6:8] == b"\x00\x01" and not (ip.is_private or ip.is_loopback) else []
    if proto == 0x0800:
        ip_proto, dst, seg = p[9], ipaddress.ip_address(p[16:20]), p[(p[0] & 15) * 4:]
    elif proto == 0x86DD:
        ip_proto, dst, seg = p[6], ipaddress.ip_address(p[24:40]), p[40:]
    else:
        return []
    if ip_proto == 6:  # TCP: a SYN without ACK opens a connection
        dport, flags = struct.unpack(">H", seg[2:4])[0], seg[13]
        if flags & 0x02 and not flags & 0x10 and not (dst.is_private or dst.is_loopback):
            return [("syn", f"{dst}:{dport}")]
    elif ip_proto == 17:
        dport, body = struct.unpack(">H", seg[2:4])[0], seg[8:]
        # Docker's DNS sits at 127.0.0.11 behind a port redirect, so match the address too.
        if (dport == 53 or str(dst) == "127.0.0.11") and len(body) > 12 and not body[2] & 0x80:
            return [("dns", dns_name(body))]
        if not (dst.is_private or dst.is_loopback):
            return [("udp", f"{dst}:{dport}")]
    return []


def dns_name(msg: bytes) -> str:
    labels, i = [], 12
    while i < len(msg) and msg[i]:
        n = msg[i]
        labels.append(msg[i + 1:i + 1 + n].decode("ascii", "replace"))
        i += 1 + n
    return ".".join(labels).lower()


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarise(box: Path) -> dict:
    settings = json.loads((box / "settings.json").read_text())
    meta = json.loads((box / "canary-meta.json").read_text())
    cfg = privacy.load_config()
    policy = privacy.Policy(cfg, settings["profile"], own=settings["own"])
    hosts: dict[str, dict] = {}
    leaks = []
    for e in load_jsonl(box / "logs" / "flows.jsonl"):
        h = hosts.setdefault(e["host"], {"host": e["host"], "requests": 0, "forwarded": 0, "blocked": 0,
                                         "tls_refused": 0, "methods": set(), "paths": []})
        if e["event"] == "request":
            h["requests"] += 1
            h["forwarded" if e["action"] == "forward" else "blocked"] += 1
            h["methods"].add(e["method"])
            if len(h["paths"]) < 5:
                h["paths"].append(f"{e['method']} {e['path'][:120]}")
            for hit in e.get("canaries", []):
                m = meta.get(hit["canary"], {})
                expected = m.get("type") == "credential" and any(privacy.host_matches(e["host"], s) for s in m["expected"])
                leaks.append({"host": e["host"], "canary": hit["canary"], "where": hit["where"],
                              "type": m.get("type"), "expected": expected, "source": m.get("file")})
        elif e["event"] == "tls-refused":
            h["tls_refused"] += 1
    for h in hosts.values():
        h["kind"], h["status"] = policy.classify(h["host"])
        h["methods"] = sorted(h["methods"])
    lookups, direct = set(), set()
    for kind, value in read_pcap(box / "logs" / "capture.pcap"):
        if kind == "dns":
            if value and "." in value and not value.endswith((".internal", ".local")):
                lookups.add(value)
        else:
            direct.add(value)
    proxied = set(hosts)
    return {
        "settings": settings,
        "hosts": sorted(hosts.values(), key=lambda h: (privacy.STATUS_ORDER.index(h["status"]), h["host"])),
        "leaks": leaks,
        "bypass_lookups": sorted(lookups - proxied),
        "bypass_connections": sorted(direct),
        "logs": {name: tail(box / "logs" / name) for name in ("install.log", "run.log")},
        "tools_listed": (box / "logs" / "tools.json").exists(),
    }


def tail(path: Path, n: int = 25) -> str:
    return "\n".join(path.read_text(errors="replace").splitlines()[-n:]) if path.exists() else "(no log)"


def format_report(s: dict) -> str:
    st = s["settings"]
    out = [
        "# Sandbox run",
        "",
        f"- Target: {st['package'] or st['target']} ({st['kind']})",
        f"- Mode: {st['mode']}; forwarded only: {', '.join(st['allow']) or 'nothing'}",
        f"- Profile: {st['profile']}" + (f"; own service: {', '.join(st['own'])}" if st["own"] else ""),
        f"- Install: `{st['install']}`",
        f"- Run: `{st['run']}`",
        "",
        "## Planted data seen on the wire",
        "",
    ]
    bad = [x for x in s["leaks"] if not x["expected"]]
    if not s["leaks"]:
        out.append("None. No request carried any canary (fake key, file or input text).")
    for x in s["leaks"]:
        label = "expected use of its own credential" if x["expected"] else "**would have left the machine**"
        out.append(f"- `{x['canary']}` ({x['source'] or 'credential'}) in the {x['where']} of a request to "
                   f"`{x['host']}`: {label}. Blocked by the sandbox.")
    out += ["", "## Hosts contacted through the proxy", ""]
    if s["hosts"]:
        out += ["| Host | Kind | Status | Requests | Forwarded | Blocked | TLS refused | Examples |", "|---|---|---|---|---|---|---|---|"]
        for h in s["hosts"]:
            out.append(f"| {h['host']} | {h['kind']} | {h['status']} | {h['requests']} | {h['forwarded']} | {h['blocked']} | "
                       f"{h['tls_refused']} | {'; '.join(f'`{p}`' for p in h['paths'][:2])} |")
    else:
        out.append("None.")
    out += ["", "## Attempts to go around the proxy", ""]
    if s["bypass_lookups"] or s["bypass_connections"]:
        if s["bypass_lookups"]:
            out.append("- DNS lookups for hosts never requested through the proxy: " + ", ".join(f"`{h}`" for h in s["bypass_lookups"]))
        if s["bypass_connections"]:
            out.append("- Direct connections or sends, not through the proxy (no route out, so they failed): "
                       + ", ".join(f"`{h}`" for h in s["bypass_connections"]))
    else:
        out.append("None seen.")
    out += ["", "## What this run can't tell you", "",
            "- Code paths this run didn't reach: other commands, tools, flags, schedules, or a later update.",
            "- Hosts refused TLS (pinned certificates): the host is known, the content isn't.",
            "- Behaviour that waits for real credentials or real accounts."]
    out += ["", "## Logs", "", "install.log (tail):", "```", s["logs"]["install.log"], "```",
            "run.log (tail):", "```", s["logs"]["run.log"], "```"]
    if s["tools_listed"]:
        out.append("\nMCP tools and their descriptions: `logs/tools.json`; calls and results: `logs/calls.jsonl`.")
    verdict = ("Planted data tried to leave the machine." if bad else
               "Unexpected hosts were contacted." if any(h["status"] in ("flag", "check") for h in s["hosts"])
               or s["bypass_lookups"] or s["bypass_connections"] else
               "Nothing unexpected was seen in this run.")
    out[1:1] = ["", f"**{verdict}**"]
    return "\n".join(out) + "\n"


# --- cli --------------------------------------------------------------------


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sandbox.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="write a sandbox folder (runs nothing)")
    p.add_argument("--work", required=True, help="the audit's work folder (from privacy.py init)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--target", help="folder with the tool's source")
    src.add_argument("--package", help="npm:<name>[@version] or pypi:<name>[==version], installed inside")
    p.add_argument("--kind", choices=("node", "python", "generic"))
    p.add_argument("--install", help="install command (default: by kind)")
    p.add_argument("--run", help="command that exercises the tool, run after install")
    p.add_argument("--mcp", help="stdio MCP server command to drive, e.g. 'node dist/index.js'")
    p.add_argument("--calls", help="MCP calls: list (default), auto, or a JSON file of [{name, arguments}]")
    p.add_argument("--mode", choices=MODES, default="registries",
                   help="block: forward nothing; registries (default): package registries only; trusted: plus your profile's trusted domains")
    p.add_argument("--allow", help="extra comma-separated domains to forward")
    p.add_argument("--own", help="the tool's own service domains (used with --mode trusted and in the report)")
    p.add_argument("--profile", choices=("work", "personal"))
    p.add_argument("--timeout", type=int, default=120, help="seconds for install, and again for run")
    p.add_argument("--linger", type=int, default=8, help="seconds to keep watching after the run (late beacons)")
    for name in ("run", "report", "clean"):
        sub.add_parser(name).add_argument("box", type=Path)
    args = ap.parse_args(argv)

    if args.cmd == "prepare":
        box = prepare(args)
        print(json.dumps({"sandbox": str(box), "settings": json.loads((box / "settings.json").read_text()),
                          "next": f"sandbox.py run {box}   (runs the target's code: ask first)"}, indent=2))
    elif args.cmd == "run":
        code = run(args.box.resolve())
        report = format_report(summarise(args.box.resolve()))
        (args.box / "sandbox-report.md").write_text(report)
        print(report)
        print(f"target exit code {code}; report saved to {args.box / 'sandbox-report.md'}")
    elif args.cmd == "report":
        report = format_report(summarise(args.box.resolve()))
        (args.box / "sandbox-report.md").write_text(report)
        print(report)
    elif args.cmd == "clean":
        compose(args.box.resolve(), "down", "--remove-orphans", "--rmi", "local", "--timeout", "2", timeout=120)


if __name__ == "__main__":
    main()
