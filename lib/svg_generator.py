"""SVG generator for the Last.fm now-playing widget (v2 design).

Self-contained SVG for embedding in a GitHub profile README via <img>.
Artwork is base64-embedded (data URI) because <img>-sandboxed SVGs cannot
make external requests — a CDN <image href> would render blank.

Layout (viewBox 0 0 480 140):
  +----------------------------------------------------+
  |  [art 96]   NOW PLAYING                            |
  |            Track Name (bold)                       |
  |            Artist                                  |
  |  [============================================]    |  <- progress bar (full width)
  +----------------------------------------------------+

State:
  playing  -> green "NOW PLAYING" label + animated green indeterminate sweep
  not      -> no label, static dim progress track, track + artist only
  empty    -> minimal fallback SVG

Track dict shape (unchanged): name, artist, album, art_url, art_b64, playing,
played_at. played_at is no longer rendered (relative time dropped in v2) but
is kept in the dict for callers/tests.
"""
from __future__ import annotations

import html
import time
from typing import Mapping, Optional

# --- layout (viewBox 0 0 480 140) ------------------------------------------
W, H = 480, 140
PAD = 16
ART = 96                 # album art square (was 128 in v1)
ART_X, ART_Y = PAD, (H - ART) // 2   # 16, 22
ART_R = 8
TEXT_X = PAD + ART + 16  # 128
# progress bar spans full card width (centered)
PB_X, PB_Y = PAD, H - 18          # 16, 122
PB_W, PB_H = W - 2 * PAD, 3       # 448 x 3
PB_R = 1.5
PB_SEG_W = 90                     # animated segment width

# --- palette (GitHub dark) -------------------------------------------------
BG = "#0d1117"
BORDER = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
LABEL_DIM = "#6e7681"
ACCENT_PLAY = "#3fb950"
PB_TRACK = "#21262d"
PLACEHOLDER_GRAD = ("#30363d", "#21262d")

TRACK_MAX = 30
ARTIST_MAX = 34

# CSS keyframes for the indeterminate progress sweep (same mechanism the
# snake SVG uses; preserved by GitHub's SVG renderer).
_PB_SWEEP = PB_W - PB_SEG_W  # px the segment travels (358)
_PB_STYLE = (
    ".pb-fill{animation:pbsweep 1.6s ease-in-out infinite alternate}"
    "@keyframes pbsweep{from{transform:translate(0,0)}"
    "to{transform:translate(" + str(_PB_SWEEP) + "px,0)}}"
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
    """Album art (96px, rounded) or a gradient placeholder with a note glyph."""
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
        f'<text x="{ART_X + ART // 2}" y="{ART_Y + ART // 2 + 8}" '
        f'text-anchor="middle" font-size="32" fill="#484f58" '
        'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        '&#9835;</text>'
    )


def _fallback_svg(message: str = "Nothing playing yet") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="{_escape(message)}">'
        f'<rect width="{W}" height="{H}" rx="12" ry="12" fill="{BG}" '
        f'stroke="{BORDER}" stroke-width="1"/>'
        f'<text x="{W // 2}" y="{H // 2}" text-anchor="middle" '
        f'dominant-baseline="middle" fill="{LABEL_DIM}" font-size="14" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        f'{_escape(message)}</text>'
        "</svg>"
    )


def _progress_bar(playing: bool) -> str:
    """Full-width centered bar: dim track always; animated green sweep when playing."""
    track = (
        f'<rect x="{PB_X}" y="{PB_Y}" width="{PB_W}" height="{PB_H}" '
        f'rx="{PB_R}" ry="{PB_R}" fill="{PB_TRACK}"/>'
    )
    if not playing:
        return track
    clip = (
        f'<clipPath id="pbclip"><rect x="{PB_X}" y="{PB_Y}" width="{PB_W}" '
        f'height="{PB_H}" rx="{PB_R}" ry="{PB_R}"/></clipPath>'
    )
    seg = (
        f'<rect class="pb-fill" x="{PB_X}" y="{PB_Y}" width="{PB_SEG_W}" '
        f'height="{PB_H}" rx="{PB_R}" ry="{PB_R}" fill="{ACCENT_PLAY}" '
        f'clip-path="url(#pbclip)"/>'
    )
    return clip + track + seg


def render_svg(track: Optional[Mapping], *, now: Optional[int] = None) -> str:
    """Render a track dict to an SVG string. Always returns valid SVG."""
    if not track or not track.get("name") or not track.get("artist"):
        return _fallback_svg()

    playing = bool(track.get("playing"))
    name = _ellipsize(str(track.get("name", "")), TRACK_MAX)
    artist = _ellipsize(str(track.get("artist", "")), ARTIST_MAX)
    art_b64 = track.get("art_b64")

    art_svg = _art_block(art_b64)
    pb_svg = _progress_bar(playing)

    # label only when playing; no "LAST PLAYED", no relative time (v2).
    # track/artist stay at fixed Y in both states so the text never jumps
    # when the label appears/disappears; the art is centered at y=70 and the
    # 2-line block is centered to match.
    label_line = ""
    if playing:
        label_line = (
            f'<text x="{TEXT_X}" y="42" fill="{ACCENT_PLAY}" font-size="10" '
            f'letter-spacing="1.6" font-weight="600" '
            f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
            'NOW PLAYING</text>'
        )

    track_y = 64
    artist_y = 86
    title_color = TEXT_PRIMARY if playing else TEXT_SECONDARY

    state = "now playing" if playing else "last played"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="Last.fm {state}: '
        f'{_escape(name)} by {_escape(artist)}">'
        f'<style>{_PB_STYLE}</style>'
        f'<rect width="{W}" height="{H}" rx="12" ry="12" fill="{BG}" '
        f'stroke="{BORDER}" stroke-width="1"/>'
        f"{art_svg}"
        f'<clipPath id="tclip"><rect x="{TEXT_X}" y="20" '
        f'width="{W - TEXT_X - PAD}" height="{PB_Y - 24}"/></clipPath>'
        f'<g clip-path="url(#tclip)">'
        f"{label_line}"
        f'<text x="{TEXT_X}" y="{track_y}" fill="{title_color}" font-size="20" '
        f'font-weight="600" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        f"{_escape(name)}</text>"
        f'<text x="{TEXT_X}" y="{artist_y}" fill="{TEXT_SECONDARY}" font-size="14" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        f'{_escape(artist)}</text>'
        f"</g>"
        f"{pb_svg}"
        "</svg>"
    )
