# Desktop apps and extensions

## Electron apps (most note-takers, transcribers and chat clients)

Unpack `app.asar` with `privacy.py unasar` (see `fetching.md`) and read:

- `package.json` `main`: the main process, which has full file system and network access.
- Preload scripts and the renderer bundle: often minified; note it in Coverage.
- `loadURL("https://…")` of a remote site: the "app" is that website in a window, and
  everything you do in it goes to that site.
- `autoUpdater` / `electron-updater` feed URLs: updates can change everything; note who
  serves them.
- `crashReporter.start({ submitURL })`: crash dumps can contain memory, which means
  anything the app was showing.
- Analytics and error SDKs, as for packages.
- Native modules in `app.asar.unpacked/` (`.node` files): binaries you can't read. If the
  audio capture or the sync engine is native, say the verdict rests on that.

### Note-takers, meeting recorders, transcribers

The questions the user cares about most:

- **Audio**: is transcription local (whisper.cpp, a bundled model) or cloud (an ASR API:
  AssemblyAI, Deepgram, OpenAI, Rev, the vendor's own backend)? Cloud means the raw
  meeting audio leaves the machine: decide at least, blocker if undisclosed.
- **Transcripts and summaries**: stored where? Synced to the vendor's cloud by default?
  Sent to an LLM for summaries? Shared with meeting participants automatically?
- **Calendar and contacts**: many read your calendar to join meetings and collect
  attendee names and emails. Where does that go?
- **Retention and training**: does the vendor say it trains on your data? Quote the
  policy if you find it; say if you couldn't.
- **Permissions**: microphone, screen recording, accessibility, calendar, contacts.
  Read the macOS entitlements with `codesign -d --entitlements - "/Applications/X.app"`
  and `Info.plist` usage strings; each one is a data source to trace.

## VS Code (and Cursor, Windsurf) extensions

- `package.json`: `activationEvents` (`"*"` or `onStartupFinished` means always running),
  `contributes`, `extensionDependencies` (audit those too).
- `@vscode/extension-telemetry` or other telemetry: does it respect
  `telemetry.telemetryLevel`? Many send their own events regardless.
- Workspace access: reading files, the git history, open editors, the terminal. On the
  work laptop this is company code; find where it goes.
- AI features: code and prompts sent to which endpoint, under whose key?
- Webviews that load remote content.

## Browser extensions

- `manifest.json` permissions: `<all_urls>` or broad `host_permissions`, `cookies`,
  `history`, `tabs`, `webRequest`, `scripting`, `clipboardRead`, `nativeMessaging`. Each is
  a data source.
- Content scripts injected on all sites can read every page, including mail and Slack in
  the browser.
- Background or service worker network calls: what's sent, especially URLs (your browsing
  history) and page content.
- Remote code: `eval`, `new Function`, scripts loaded from a server (Manifest V2), or
  "remote config" that changes what the extension collects.
- `externally_connectable`: which websites can talk to the extension.

## Binary-only and closed-source apps

There's no code to read. Say so, and give what you can: the vendor's stated data
practices (quoted, with a link), entitlements, hosts found with `strings`, and a verdict
of Can't tell unless the evidence is decisive. The sandbox can't run macOS GUI apps;
suggest a network monitor the user runs themselves (LuLu is free and open source; Little
Snitch is paid) to watch what the app contacts during a real meeting.
