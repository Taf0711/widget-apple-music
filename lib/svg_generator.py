"""SVG generator for the Last.fm now-playing widget (compact/embedded design).

Self-contained SVG for embedding in a GitHub profile README via <img>.
Artwork is base64-embedded (data URI) because <img>-sandboxed SVGs cannot
make external requests — a CDN <image href> would render blank.

Compact layout (viewBox 0 0 400 84) — dense, badge-like, sits inline:
  +----------------------------------------------+
  | [art]  NOW PLAYING                  [eq bars] |
  |        Track Name (bold)                     |
  |        Artist                                |
  +----------------------------------------------+

State:
  playing  -> green "NOW PLAYING" label + 4 animated green equalizer bars
  not      -> no label, no equalizer, dimmed track + artist
  empty    -> minimal fallback SVG

Track dict shape (unchanged): name, artist, album, art_url, art_b64, playing,
played_at. played_at is no longer rendered (relative time dropped in v2) but
is kept in the dict for callers/tests.
"""
from __future__ import annotations

import html
import time
from typing import Mapping, Optional

# --- layout (viewBox 0 0 400 84) — compact/embedded -----------------------
W, H = 400, 84
PAD = 10
ART = 56                          # album art square (was 96)
ART_X, ART_Y = PAD, (H - ART) // 2   # 10, 14
ART_R = 6
TEXT_X = PAD + ART + 12           # 78
# equalizer bars: 4 bars at the right edge, vertically centered with text
EQ_BAR_W = 3
EQ_GAP = 3
EQ_COUNT = 4
EQ_TOTAL_W = EQ_COUNT * EQ_BAR_W + (EQ_COUNT - 1) * EQ_GAP  # 21
EQ_X = W - PAD - EQ_TOTAL_W      # 369 (right-aligned)
EQ_BASE_Y = H - 14               # 70 (bottom baseline)
EQ_MAX_H = 10

# --- palette (GitHub dark, aligned with terminal header) --------------------
BG = "#0d1117"
BORDER = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
LABEL_DIM = "#6e7681"
ACCENT_PLAY = "#3fb950"
ACCENT_DIM = "#2ea043"  # dimmer green for 'LAST PLAYED'
PLACEHOLDER_GRAD = ("#30363d", "#21262d")
FONT_MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

TRACK_MAX = 26
ARTIST_MAX = 28

# CSS keyframes: 4 equalizer bars bounce at different speeds/delays for an
# organic "playing" feel. Each bar scales vertically from its bottom edge.
# Uses transform:scaleY (proven by the snake SVG on GitHub).
_EQ_DURS = ["0.9s", "1.2s", "0.7s", "1.1s"]  # per-bar durations
_EQ_DELAYS = ["0s", "0.3s", "0.1s", "0.5s"]  # per-bar delays
_EQ_STYLE = (
    ".eq-bar{transform-origin:0 " + str(EQ_BASE_Y) + "px;"
    "animation:eqbounce 0.9s ease-in-out infinite alternate}"
    "@keyframes eqbounce{0%{transform:scaleY(0.3)}"
    "50%{transform:scaleY(0.8)}100%{transform:scaleY(0.5)}}"
)
for _i in range(EQ_COUNT):
    _EQ_STYLE += (
        ".eq-" + str(_i) + "{animation-duration:" + _EQ_DURS[_i]
        + ";animation-delay:" + _EQ_DELAYS[_i] + "}"
    )


def _escape(s: str) -> str:
    return html.escape(s, quote=True)


def _ellipsize(s: str, limit: int) -> str:
    s = s.strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "\u2026"


def _relative_time(played_at: Optional[int], now: Optional[int] = None) -> str:
    """Kept for callers/tests; no longer rendered in the v2 card."""
    if not played_at:
        return ""
    now = int(now if now is not None else time.time())
    secs = max(0, now - int(played_at))
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60} min ago"
    if secs < 86400:
        return f"{secs // 3600} hr ago"
    days = secs // 86400
    if days < 7:
        return f"{days} d ago"
    return f"{days // 7} wk ago"


def _art_block(art_b64: Optional[str]) -> str:
    """Album art (56px, rounded) or a gradient placeholder with a note glyph."""
    if art_b64:
        return (
            f'<clipPath id="artclip"><rect x="{ART_X}" y="{ART_Y}" '
            f'width="{ART}" height="{ART}" rx="{ART_R}" ry="{ART_R}"/></clipPath>'
            f'<image x="{ART_X}" y="{ART_Y}" width="{ART}" height="{ART}" '
            f'href="{_escape(art_b64)}" preserveAspectRatio="xMidYMid slice" '
            f'clip-path="url(#artclip)"/>'
        )
    return (
        f'<defs><linearGradient id="artph" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{PLACEHOLDER_GRAD[0]}"/>'
        f'<stop offset="1" stop-color="{PLACEHOLDER_GRAD[1]}"/></linearGradient></defs>'
        f'<rect x="{ART_X}" y="{ART_Y}" width="{ART}" height="{ART}" '
        f'rx="{ART_R}" ry="{ART_R}" fill="url(#artph)"/>'
        f'<text x="{ART_X + ART // 2}" y="{ART_Y + ART // 2 + 6}" '
        f'text-anchor="middle" font-size="24" fill="#484f58" '
        f'font-family="{FONT_MONO}">'
        '&#9835;</text>'
    )


def _fallback_svg(message: str = "Nothing playing yet") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="{_escape(message)}">'
        f'<rect width="{W}" height="{H}" rx="6" ry="6" fill="{BG}" '
        f'stroke="{BORDER}" stroke-width="1"/>'
        f'<text x="{W // 2}" y="{H // 2}" text-anchor="middle" '
        f'dominant-baseline="middle" fill="{LABEL_DIM}" font-size="12" '
        f'font-family="{FONT_MONO}">'
        f'{_escape(message)}</text>'
        "</svg>"
    )


def _equalizer(playing: bool) -> str:
    """4 green bars bouncing at different speeds when playing; nothing when not."""
    if not playing:
        return ""
    bars = ""
    for i in range(EQ_COUNT):
        bx = EQ_X + i * (EQ_BAR_W + EQ_GAP)
        bars += (
            f'<rect class="eq-bar eq-{i}" x="{bx}" '
            f'y="{EQ_BASE_Y - EQ_MAX_H}" width="{EQ_BAR_W}" '
            f'height="{EQ_MAX_H}" rx="1" fill="{ACCENT_PLAY}"/>'
        )
    return bars


def render_svg(track: Optional[Mapping], *, now: Optional[int] = None) -> str:
    """Render a track dict to an SVG string. Always returns valid SVG."""
    if not track or not track.get("name") or not track.get("artist"):
        return _fallback_svg()

    playing = bool(track.get("playing"))
    name = _ellipsize(str(track.get("name", "")), TRACK_MAX)
    artist = _ellipsize(str(track.get("artist", "")), ARTIST_MAX)
    art_b64 = track.get("art_b64")

    art_svg = _art_block(art_b64)
    eq_svg = _equalizer(playing)

    # label only when playing; no "LAST PLAYED", no relative time (v2).
    # track/artist stay at fixed Y in both states so the text never jumps
    # when the label appears/disappears. Art is centered at y=42; the 2-line
    # text block is centered to match.
    label_line = ""
    if playing:
        label_line = (
            f'<text x="{TEXT_X}" y="24" fill="{ACCENT_PLAY}" font-size="8" '
            f'letter-spacing="1.2" font-weight="600" '
            f'font-family="{FONT_MONO}">'
            'NOW PLAYING</text>'
        )
    else:
        label_line = (
            f'<text x="{TEXT_X}" y="24" fill="{ACCENT_DIM}" font-size="8" '
            f'letter-spacing="1.2" font-weight="600" '
            f'font-family="{FONT_MONO}">'
            'LAST PLAYED</text>'
        )

    track_y = 42
    artist_y = 60
    title_color = TEXT_PRIMARY if playing else TEXT_SECONDARY
    font_family = FONT_MONO

    state = "now playing" if playing else "last played"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="Last.fm {state}: '
        f'{_escape(name)} by {_escape(artist)}">'
        f'<style>{_EQ_STYLE}</style>'
        f'<rect width="{W}" height="{H}" rx="6" ry="6" fill="{BG}" '
        f'stroke="{BORDER}" stroke-width="1"/>'
        f"{art_svg}"
        # text column clip: leaves room for the equalizer at the right edge
        f'<clipPath id="tclip"><rect x="{TEXT_X}" y="10" '
        f'width="{EQ_X - TEXT_X - 6}" height="{H - 20}"/></clipPath>'
        f'<g clip-path="url(#tclip)">'
        f"{label_line}"
        f'<text x="{TEXT_X}" y="{track_y}" fill="{title_color}" font-size="13" '
        f'font-weight="600" '
        f'font-family="{font_family}">'
        f"{_escape(name)}</text>"
        f'<text x="{TEXT_X}" y="{artist_y}" fill="{TEXT_SECONDARY}" font-size="10" '
        f'font-family="{font_family}">'
        f'{_escape(artist)}</text>'
        f"</g>"
        f"{eq_svg}"
        "</svg>"
    )
