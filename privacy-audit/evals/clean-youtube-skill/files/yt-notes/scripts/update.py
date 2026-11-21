"""Once a day, tell the user if a newer release of yt-notes exists."""

import json
import time
import urllib.request
from pathlib import Path

VERSION = "1.3.0"
STAMP = Path("~/.cache/yt-notes/last-update-check").expanduser()


def check_for_update():
    if STAMP.exists() and time.time() - STAMP.stat().st_mtime < 86400:
        return
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.touch()
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/ytnotesdev/yt-notes/releases/latest",
            headers={"User-Agent": f"yt-notes/{VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            latest = json.load(r)["tag_name"].lstrip("v")
        if latest != VERSION:
            print(f"(yt-notes {latest} is available; you have {VERSION})")
    except Exception:
        pass
