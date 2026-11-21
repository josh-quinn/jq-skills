#!/usr/bin/env python3
"""Print a YouTube video's title and transcript (captions only, no video)."""

import json
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from update import check_for_update


def title(url: str) -> str:
    q = urllib.parse.urlencode({"url": url, "format": "json"})
    with urllib.request.urlopen(f"https://www.youtube.com/oembed?{q}", timeout=10) as r:
        return json.load(r)["title"]


def captions(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["yt-dlp", "--skip-download", "--write-auto-subs", "--sub-format", "vtt",
             "--sub-langs", "en.*", "-o", f"{tmp}/%(id)s.%(ext)s", url],
            check=True, capture_output=True,
        )
        files = sorted(Path(tmp).glob("*.vtt"))
        return files[0].read_text() if files else ""


if __name__ == "__main__":
    url = sys.argv[1]
    check_for_update()
    print(title(url))
    print(captions(url))
