#!/usr/bin/env python3
"""Save notes from stdin to the notes folder."""

import os
import sys
from pathlib import Path

folder = Path(os.environ.get("YT_NOTES_DIR", "~/video-notes")).expanduser()
folder.mkdir(parents=True, exist_ok=True)
path = folder / f"{sys.argv[1]}.md"
path.write_text(sys.stdin.read())
print(path)
