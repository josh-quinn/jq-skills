#!/usr/bin/env python3
"""Drive a stdio MCP server inside the sandbox: initialize, list its tools, and make the
tool calls in calls.json (or, with --calls auto, call every tool with canary values).

    mcp_drive.py --calls /sandbox/calls.json --out /logs -- npx -y some-mcp-server

Writes tools.json (names, descriptions and schemas, worth reading for hidden
instructions) and calls.jsonl (each call and its result) to --out.
"""

from __future__ import annotations

import argparse
import json
import os
import select
import subprocess
import sys
import time


def fill(schema: dict, text: str):
    """A value for a JSON schema, using canary text for every string."""
    t = schema.get("type")
    if "enum" in schema:
        return schema["enum"][0]
    if t == "object" or "properties" in schema:
        req = schema.get("required", list(schema.get("properties", {})))
        return {k: fill(v, text) for k, v in schema.get("properties", {}).items() if k in req}
    if t == "array":
        return [fill(schema.get("items", {"type": "string"}), text)]
    if t in ("integer", "number"):
        return 1
    if t == "boolean":
        return False
    return text


class Client:
    def __init__(self, cmd: list[str], timeout: float):
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr)
        self.timeout, self.next_id = timeout, 1

    def send(self, msg: dict):
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        self.proc.stdin.flush()

    def call(self, method: str, params: dict | None = None) -> dict:
        rid = self.next_id
        self.next_id += 1
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            ready, _, _ = select.select([self.proc.stdout], [], [], 1)
            if not ready:
                if self.proc.poll() is not None:
                    return {"error": f"server exited with {self.proc.returncode}"}
                continue
            line = self.proc.stdout.readline()
            if not line:
                return {"error": "server closed stdout"}
            try:
                msg = json.loads(line)
            except ValueError:
                continue  # a server logging to stdout
            if msg.get("id") == rid:
                return msg
        return {"error": f"no answer to {method} in {self.timeout}s"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", default="list", help="'list', 'auto', or a JSON file of [{name, arguments}]")
    ap.add_argument("--out", default="/logs")
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--canary-text", default=os.environ.get("SANDBOX_CANARY_TEXT", "canary"))
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    client = Client(cmd, args.timeout)
    init = client.call("initialize", {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "privacy-sandbox", "version": "1"},
    })
    client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    tools = client.call("tools/list").get("result", {}).get("tools", [])
    with open(os.path.join(args.out, "tools.json"), "w") as f:
        json.dump({"initialize": init, "tools": tools}, f, indent=2)
    if args.calls == "list":
        calls = []
    elif args.calls == "auto":
        calls = [{"name": t["name"], "arguments": fill(t.get("inputSchema", {}), args.canary_text)} for t in tools]
    else:
        calls = json.load(open(args.calls))
    with open(os.path.join(args.out, "calls.jsonl"), "w") as f:
        for c in calls:
            result = client.call("tools/call", {"name": c["name"], "arguments": c.get("arguments", {})})
            f.write(json.dumps({"call": c, "result": result})[:20000] + "\n")
    print(f"mcp_drive: {len(tools)} tools listed, {len(calls)} called", file=sys.stderr)
    client.proc.terminate()


if __name__ == "__main__":
    main()
