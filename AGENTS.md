# Cider Now Playing — Project Blueprint

> Agent instruction file for `cider-now-playing`. This is the canonical reference for
> any agent (Codex, Zed, Pi, Claude) working on this project. Read this first.

## What this project is

A live "now playing" widget for a GitHub profile README that shows what's
currently (or most recently) playing in Apple Music — without the $99/year
Apple Developer account, without Spotify, without Last.fm as a middleman.

It works by polling Cider's local RPC API (`localhost:10767`), generating an
SVG on track change, and committing that SVG to the GitHub profile repo
(`Taf0711/Taf0711`) so it renders in the README.

### Architecture (push model, no tunnel)

```
Apple Music  →  Cider app (local RPC at localhost:10767)
                        ↓
               poller script (this repo, runs on Mac)
                        ↓
               generates SVG (track name, artist, album art)
                        ↓
               git commit + push to Taf0711/Taf0711 (output branch or main)
                        ↓
               GitHub README displays the SVG
```

The poller runs as a background process on the Mac. It polls Cider's
`/api/v1/playback/now-playing` endpoint every ~5 seconds. On track change
(or play/pause state change), it regenerates the SVG and commits it. No
external server, no tunnel, no ongoing hosting cost.

### Why push model (not tunnel)

- **No tunnel to maintain.** Cloudflare Tunnel / ngrok exposes localhost to
  the internet — another moving part that can break, rate-limit, or go stale.
- **GitHub-native.** The SVG lives in the repo, renders as a raw image URL,
  and is cached by GitHub's CDN. The README just references
  `https://raw.githubusercontent.com/Taf0711/Taf0711/<branch>/now-playing.svg`.
- **Offline-safe.** If the Mac is asleep or Cider is closed, the SVG shows
  the last-played track (stale but not broken). A tunnel would 502.

## Components

### 1. `poller.py` — the daemon

- Polls `http://localhost:10767/api/v1/playback/now-playing` every N seconds.
- Sends Cider API token in `apptoken` header.
- Diffs the current track against the last-seen track (by `playParams.id` or
  `name + artistName`).
- On change (new track, or play → pause, or pause → play), calls the SVG
  generator and commits the result.
- Handles Cider being closed: if the API is unreachable, do nothing (keep
  showing the last-known SVG). Don't crash, don't spam commits.
- Graceful shutdown on SIGTERM/SIGINT.

### 2. `svg_generator.py` — SVG rendering

- Takes the Cider now-playing JSON payload, returns an SVG string.
- Fetches album artwork from the `artwork.url` field (Apple's CDN,
  `is1-ssl.mzstatic.com` — public, no auth needed).
- Embeds artwork as a base64 data URI inside the SVG (so the SVG is
  self-contained — one file, no external image dependency that could break).
- Layout: album art on the left, "now playing" label + track name + artist
  on the right. Dark background, clean typography.
- Two states:
  - **Playing**: full color, maybe a subtle "▶" or animated equalizer bars
    (CSS animation inside SVG works in GitHub's raw rendering).
  - **Paused / last played**: dimmed or a "last played" label instead of
    "now playing".
- Size: ~640x200px (matches the visual weight of the snake graph above it
  in the README).

### 3. `git_publisher.py` — commit + push

- Uses `git` CLI (simpler than PyGithub for a single-file commit).
- Clones or pulls the `Taf0711/Taf0711` repo to a local working dir.
- Writes `now-playing.svg` to the working dir.
- Commits with message like `chore(now-playing): <track> — <artist>`.
- Pushes to a dedicated branch (`now-playing` or `output`) so the main
  branch history stays clean and doesn't get flooded with track-change
  commits.
- Uses a GitHub PAT stored in environment variable `GH_TOKEN` (or
  `~/.config/gh-token`). Never commit the token.
- Dedup: if the generated SVG is byte-identical to what's already there,
  skip the commit (no-op, don't spam the git log).

### 4. `launchd` plist — auto-start on login

- `~/Library/LaunchAgents/com.tafseer.cider-now-playing.plist`
- Runs `python3 poller.py` on login, restarts on crash (`KeepAlive: true`).
- Logs to `~/.cider-now-playing/poller.log` and `poller.err`.

### 5. Config — `config.json` or env vars

```json
{
  "cider_api_url": "http://localhost:10767",
  "cider_api_token": "<from Cider settings>",
  "github_repo": "Taf0711/Taf0711",
  "github_branch": "now-playing",
  "github_token": "<env: GH_TOKEN>",
  "poll_interval_seconds": 5,
  "svg_width": 640,
  "svg_height": 200
}
```

Token in env var, not in the JSON. The JSON is for non-secret config only.

## Cider API reference (verified)

Source: `ciderapp/Cider-Docs` → `docs/1.client/rpc.md`

- **Base URL**: `http://localhost:10767`
- **Auth**: `apptoken` header (token generated in Cider → Settings →
  Connectivity → Manage External Application Access to Cider). No `Bearer`
  prefix.
- **`GET /api/v1/playback/now-playing`** — returns the full track object:
  ```json
  {
    "status": "ok",
    "info": {
      "name": "Like Water (feat. MNDR)",
      "artistName": "Flume",
      "albumName": "Skin",
      "artwork": {
        "width": 600, "height": 600,
        "url": "https://is1-ssl.mzstatic.com/image/thumb/.../640x640sr.jpg"
      },
      "url": "https://music.apple.com/.../1719860281?i=1719861213",
      "durationInMillis": 193633,
      "currentPlaybackTime": 2.066576,
      "playParams": { "id": "1719861213", "kind": "song" }
    }
  }
  ```
  The artwork URL uses `{w}` and `{h}` placeholders — replace with desired
  pixel dimensions (e.g. 300x300 for the SVG).
- **`GET /api/v1/playback/is-playing`** — returns `{"is_playing": true/false}`.
  Use this for the playing/paused state without fetching the full payload.
- **`GET /api/v1/playback/queue`** — includes playback history items.
  Could be used for a "recently played" list if we want to expand later.

When no track is playing, `now-playing` returns `{"status": "ok", "info": null}`
or an empty `info` object — handle this gracefully (show "nothing playing"
or keep the last-known track).

## Prerequisites (what Tafseer needs to do before the code works)

1. **Install Cider** from [cider.sh](https://cider.sh) (or
   `brew install --cask cider` if available).
2. **Sign in to Apple Music** in Cider (uses your existing Apple ID /
   Apple Music subscription — no developer account needed).
3. **Enable the RPC API**: Cider → Settings → Connectivity → Manage
   External Application Access → generate a token. Copy it.
4. **Generate a GitHub PAT** with `repo` scope at
   https://github.com/settings/tokens (classic PAT is fine, or fine-grained
   with write access to `Taf0711/Taf0711`).
5. **Set the token in env**: `export GH_TOKEN=ghp_...` (add to
   `~/.zshrc` or a launchd `EnvironmentVariables` dict).
6. **Put the Cider API token** in `config.json` (or env var
   `CIDER_API_TOKEN`).

## File structure

```
cider-now-playing/
├── AGENTS.md              ← this file
├── README.md              ← setup + usage docs (written after MVP works)
├── config.json            ← non-secret config (cider url, poll interval, svg size)
├── .gitignore             ← ignore config.json if it ever holds secrets, *.log, working/
├── poller.py              ← daemon: poll Cider, diff, trigger publish
├── svg_generator.py      ← JSON → SVG string
├── git_publisher.py      ← commit + push SVG to GitHub
├── templates/
│   └── now-playing.svg    ← Jinja2 or string-template SVG skeleton
├── scripts/
│   └── install.sh         ← installs launchd plist, sets up working dir
└── tests/
    └── test_svg_generator.py  ← unit tests: payload → SVG (no network)
```

## Build order (MVP → polish)

### Phase 1 — Manual proof of concept (get one SVG committed by hand)
- [ ] Write `svg_generator.py` with a hardcoded sample Cider payload.
- [ ] Generate an SVG, verify it looks right locally.
- [ ] Manually commit it to `Taf0711/Taf0711` and verify it renders in the
      README.
- [ ] This proves the SVG → GitHub → README pipeline works before automating
      anything.

### Phase 2 — Wire up the poller
- [ ] Write `poller.py`: poll Cider, print the current track to stdout.
- [ ] Add diffing: detect track change vs last-seen.
- [ ] On change, call `svg_generator` then `git_publisher`.
- [ ] Run manually, verify it commits on track change.

### Phase 3 — Daemonize
- [ ] Write the launchd plist.
- [ ] `launchctl load` it, verify it survives a restart.
- [ ] Logs to `~/.cider-now-playing/`.

### Phase 4 — Polish
- [ ] Playing vs paused states in the SVG.
- [ ] Album art as embedded base64 (not external URL).
- [ ] Animated equalizer bars (CSS-in-SVG) when playing.
- [ ] Handle Cider closed / API unreachable gracefully.
- [ ] Dedup: don't commit if SVG is byte-identical.
- [ ] "Last played" fallback with timestamp when nothing is currently playing.

## Design constraints

- **Python 3** (stdlib + `requests` only — no heavy deps, matches the
  resume-forge project's no-venv-preferred ethos).
- **One process, one file.** The whole thing is one daemon doing
  poll → render → commit. No server, no database, no queue.
- **Idempotent.** Running the poller twice shouldn't double-commit.
- **Quiet by default.** Logs go to a file, not stdout (it's a daemon).
  Print to stdout only in `--verbose` mode.
- **No PII.** The committed SVG contains track name, artist, album art, and
  a link to the song on Apple Music. No account info, no listening history,
  no location. This is public on the GitHub profile.

## Decisions still open

- **Branch name**: `now-playing` (dedicated, clean main branch) vs
  `output` (already used by the snake graph workflow). Leaning
  `now-playing` to keep concerns separate.
- **Artwork embedding**: base64-in-SVG (self-contained, bigger file but no
  external dependency) vs raw mzstatic URL (smaller, but Apple could change
  the URL format). Leaning base64 for durability.
- **Commit message format**: `chore(now-playing): <track> — <artist>` vs
  just `🔄 now-playing`. Leaning the former — searchable, parseable.

## Related repos

- Profile repo: https://github.com/Taf0711/Taf0711 (where the SVG lands)
- Cider source: https://github.com/ciderapp/Cider-2
- Cider RPC docs: https://github.com/ciderapp/Cider-Docs/blob/main/docs/1.client/rpc.md
- Snake graph workflow (existing, for reference on how the profile repo
  already uses GitHub Actions + an `output` branch)
