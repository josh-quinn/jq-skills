---
name: yt-notes
description: Turn a YouTube video into study notes. Use when the user shares a YouTube link and wants notes, a summary, key points or flashcards from it.
---

# YouTube notes

1. Run `python3 scripts/fetch.py <youtube url>`. It downloads the video's captions (no
   video) with yt-dlp and prints the title and transcript.
2. Write notes from the transcript: a one-paragraph summary, the key points, and five
   flashcards. Quote timestamps for each key point.
3. Save them with `python3 scripts/save.py <video id>` (pass the notes on stdin). Notes go
   to `~/video-notes/<video id>.md`, or to `YT_NOTES_DIR` if the user set it.

Never upload the notes anywhere; they're for the user's own folder.
