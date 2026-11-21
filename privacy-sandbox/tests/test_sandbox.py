import base64
import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "assets"))
import addon  # noqa: E402
import mcp_drive  # noqa: E402
import sandbox  # noqa: E402


@pytest.fixture(autouse=True)
def config_root(tmp_path, monkeypatch):
    monkeypatch.setenv("JQ_TOOLS_CONFIG", str(tmp_path / "jq-tools"))
    monkeypatch.delenv("PRIVACY_AUDIT_PROFILE", raising=False)


# --- addon ------------------------------------------------------------------

CANARY = "cnry0123456789abcdef0123"


@pytest.mark.parametrize(
    "body",
    [
        f"key={CANARY}",
        json.dumps({"b64": base64.b64encode(f"notes: {CANARY} end".encode()).decode()}),
        json.dumps({"b64": base64.b64encode(f"x{CANARY}".encode()).decode()}),
        json.dumps({"b64": base64.b64encode(f"xy{CANARY}".encode()).decode()}),
        base64.urlsafe_b64encode(f"..{CANARY}..".encode()).decode(),
        CANARY.encode().hex(),
        "q=" + "%63%6e%72%79" + CANARY[4:],
    ],
)
def test_canary_found_in_any_encoding(body):
    assert addon.canary_hits({"file:x": CANARY}, {"body": body}) == [{"canary": "file:x", "where": "body"}]


def test_no_canary_no_hit():
    assert addon.canary_hits({"file:x": CANARY}, {"url": "https://a.io/x", "body": b"hello"}) == []


def test_host_allowed_covers_subdomains_only():
    assert addon.host_allowed("files.pythonhosted.org", ["pythonhosted.org"])
    assert not addon.host_allowed("evilpythonhosted.org", ["pythonhosted.org"])


# --- pcap -------------------------------------------------------------------


def sll2(proto: int, payload: bytes) -> bytes:
    return struct.pack(">H", proto) + b"\0" * 18 + payload


def ipv4(proto: int, dst: str, seg: bytes) -> bytes:
    return bytes([0x45, 0]) + b"\0" * 7 + bytes([proto]) + b"\0" * 6 + bytes(map(int, dst.split("."))) + seg


def dns_query(name: str) -> bytes:
    q = b"".join(bytes([len(x)]) + x.encode() for x in name.split(".")) + b"\0\0\x01\0\x01"
    return b"\x12\x34\x01\x00\x00\x01" + b"\0" * 6 + q


def write_pcap(path: Path, packets: list[bytes]):
    out = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 512, 276)
    for p in packets:
        out += struct.pack("<IIII", 0, 0, len(p), len(p)) + p
    path.write_bytes(out)


def test_read_pcap_finds_dns_syn_udp_and_arp(tmp_path):
    udp_dns = struct.pack(">HHHH", 40000, 33621, 0, 0) + dns_query("evil.example.xyz")
    syn = struct.pack(">HH", 40001, 443) + b"\0" * 9 + bytes([0x02]) + b"\0" * 6
    syn_to_proxy = struct.pack(">HH", 40002, 8080) + b"\0" * 9 + bytes([0x02]) + b"\0" * 6
    udp = struct.pack(">HHHH", 40003, 5353, 0, 0) + b"hello"
    arp = b"\0\x01\x08\x00\x06\x04\x00\x01" + b"\0" * 16 + bytes([1, 1, 1, 1])
    arp_inside = b"\0\x01\x08\x00\x06\x04\x00\x01" + b"\0" * 16 + bytes([192, 168, 107, 2])
    path = tmp_path / "capture.pcap"
    write_pcap(path, [
        sll2(0x0800, ipv4(17, "127.0.0.11", udp_dns)),
        sll2(0x0800, ipv4(6, "93.184.216.34", syn)),
        sll2(0x0800, ipv4(6, "172.18.0.2", syn_to_proxy)),
        sll2(0x0800, ipv4(17, "9.9.9.9", udp)),
        sll2(0x0806, arp),
        sll2(0x0806, arp_inside),
    ])
    assert sandbox.read_pcap(path) == [
        ("dns", "evil.example.xyz"), ("syn", "93.184.216.34:443"), ("udp", "9.9.9.9:5353"), ("arp", "1.1.1.1"),
    ]


# --- prepare and report -----------------------------------------------------


def prepare(tmp_path, *extra):
    target = tmp_path / "tool"
    target.mkdir()
    (target / "package.json").write_text("{}")
    args = sandbox.argparse.Namespace(**{
        "work": str(tmp_path / "work"), "target": str(target), "package": None, "kind": None, "install": None,
        "run": None, "mcp": None, "calls": None, "mode": "registries", "allow": None, "own": None, "profile": None,
        "timeout": 60, "linger": 1,
    })
    for flag, value in zip(extra[::2], extra[1::2]):
        setattr(args, flag.lstrip("-"), value)
    return sandbox.prepare(args)


def test_prepare_plants_canaries_and_writes_compose(tmp_path):
    box = prepare(tmp_path)
    canaries = json.loads((box / "sandbox/canaries.json").read_text())
    assert canaries["file:ssh-key"] in (box / "home/.ssh/id_ed25519").read_text()
    assert canaries["env:SLACK_BOT_TOKEN"].startswith("xoxb-")
    env = (box / "sandbox/target.env").read_text()
    assert "HTTPS_PROXY=http://proxy:8080" in env and canaries["env:OPENAI_API_KEY"] in env
    compose = (box / "compose.yaml").read_text()
    assert "internal: true" in compose and "registry.npmjs.org" in compose
    assert str(tmp_path / "tool") in compose
    assert json.loads((box / "settings.json").read_text())["install"] == "npm install --no-audit --no-fund"


def test_block_mode_forwards_nothing(tmp_path):
    box = prepare(tmp_path, "--mode", "block")
    assert json.loads((box / "settings.json").read_text())["allow"] == []


def test_report_separates_expected_credential_use_from_leaks(tmp_path):
    box = prepare(tmp_path, "--own", "slack.com")
    canaries = json.loads((box / "sandbox/canaries.json").read_text())
    flows = [
        {"event": "request", "host": "slack.com", "method": "POST", "path": "/api/chat.postMessage", "action": "block",
         "canaries": [{"canary": "env:SLACK_BOT_TOKEN", "where": "headers"}]},
        {"event": "request", "host": "sync.evil.xyz", "method": "POST", "path": "/u", "action": "block",
         "canaries": [{"canary": "env:SLACK_BOT_TOKEN", "where": "body"}, {"canary": "file:meeting-notes", "where": "body"}]},
        {"event": "request", "host": "registry.npmjs.org", "method": "GET", "path": "/x", "action": "forward", "canaries": []},
    ]
    (box / "logs/flows.jsonl").write_text("".join(json.dumps(f) + "\n" for f in flows))
    s = sandbox.summarise(box)
    leaks = {(x["host"], x["canary"]): x["expected"] for x in s["leaks"]}
    assert leaks == {("slack.com", "env:SLACK_BOT_TOKEN"): True, ("sync.evil.xyz", "env:SLACK_BOT_TOKEN"): False,
                     ("sync.evil.xyz", "file:meeting-notes"): False}
    text = sandbox.format_report(s)
    assert "**Planted data tried to leave the machine.**" in text
    assert "expected use of its own credential" in text
    assert canaries["file:meeting-notes"] not in text  # the report names canaries, never their values


# --- mcp driver -------------------------------------------------------------


def test_fill_uses_canary_text_for_required_strings():
    schema = {"type": "object", "properties": {"text": {"type": "string"}, "n": {"type": "integer"},
                                                 "opt": {"type": "string"}}, "required": ["text", "n"]}
    assert mcp_drive.fill(schema, "CANARY") == {"text": "CANARY", "n": 1}
