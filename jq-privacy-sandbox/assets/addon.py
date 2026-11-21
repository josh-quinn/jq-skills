"""mitmproxy addon for privacy-sandbox: log every request, forward only allowed hosts,
and never let a canary out.

Environment (set by compose.yaml):
    SANDBOX_ALLOW          comma-separated domains to forward (a domain covers its subdomains)
    SANDBOX_CANARIES_FILE  JSON {id: value} of planted fake data
    SANDBOX_LOG            JSON-lines log to append to

The pure functions at the top are tested on the host without mitmproxy installed.
"""

from __future__ import annotations

import base64
import json
import os
import time
from urllib.parse import quote, unquote_plus


def host_allowed(host: str, allow: list[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in allow)


def encodings(value: str) -> set[str]:
    """Forms a canary might take on the wire: as is, URL-encoded, hex, and base64 at
    each of the three alignments (so it is found inside a longer base64 string too)."""
    raw = value.encode()
    forms = {value, quote(value, safe=""), raw.hex()}
    for pad in range(3):
        enc = base64.b64encode(b"\0" * pad + raw).decode().rstrip("=")
        start = 4 if pad else 0
        forms.add(enc[start:-4] if len(enc) - start > 12 else enc[start:])
        forms.add(base64.urlsafe_b64encode(b"\0" * pad + raw).decode().rstrip("=")[start:-4])
    return {f for f in forms if len(f) >= 8}


def canary_hits(canaries: dict[str, str], parts: dict[str, bytes | str]) -> list[dict]:
    """Which canaries appear in which part of a request (url, headers, body)."""
    hits = []
    for cid, value in canaries.items():
        forms = encodings(value)
        for where, blob in parts.items():
            text = blob.decode("latin-1") if isinstance(blob, bytes) else blob
            variants = (text, unquote_plus(text))
            if any(f in v for f in forms for v in variants):
                hits.append({"canary": cid, "where": where})
    return hits


class Sandbox:
    def __init__(self):
        self.allow = [d.strip().lower() for d in os.environ.get("SANDBOX_ALLOW", "").split(",") if d.strip()]
        path = os.environ.get("SANDBOX_CANARIES_FILE")
        self.canaries = {}
        if path and os.path.exists(path):
            with open(path) as f:
                self.canaries = json.load(f)
        self.log_path = os.environ.get("SANDBOX_LOG", "/logs/flows.jsonl")

    def log(self, **entry):
        entry["t"] = round(time.time(), 3)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def request(self, flow):
        from mitmproxy import http

        req = flow.request
        host = req.pretty_host
        body = req.get_content(strict=False) or b""
        headers = "\n".join(f"{k}: {v}" for k, v in req.headers.items(multi=True))
        hits = canary_hits(self.canaries, {"url": req.pretty_url, "headers": headers, "body": body})
        allowed = host_allowed(host, self.allow) and not hits
        flow.metadata["sandbox"] = {"host": host, "hits": hits, "allowed": allowed}
        self.log(
            event="request", host=host, method=req.method, path=req.path[:300], scheme=req.scheme,
            bytes=len(body), action="forward" if allowed else "block", canaries=hits,
            content_type=req.headers.get("content-type", ""), body_preview=body[:300].decode("utf-8", "replace"),
        )
        if not allowed:
            reason = "canary" if hits else "not allowed"
            flow.response = http.Response.make(403, f"blocked by privacy-sandbox ({reason})".encode(), {"Content-Type": "text/plain"})

    def response(self, flow):
        meta = flow.metadata.get("sandbox") or {}
        if meta.get("allowed"):
            self.log(event="response", host=meta["host"], status=flow.response.status_code)

    def tls_failed_client(self, data):
        # The client refused our certificate: certificate pinning, or a client that ignores
        # the CA settings. We know the host it wanted, not what it would have sent.
        sni = getattr(data.context.client, "sni", None)
        self.log(event="tls-refused", host=sni or "?", error=str(getattr(data.conn, "error", ""))[:200])

    def error(self, flow):
        meta = flow.metadata.get("sandbox") or {}
        self.log(event="error", host=meta.get("host") or flow.request.pretty_host, error=str(flow.error)[:200])


addons = [Sandbox()]
