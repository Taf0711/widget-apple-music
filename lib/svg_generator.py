"""SVG generator for the Last.fm now-playing widget.

Turns a parsed Last.fm track dict into a self-contained SVG string suitable
for embedding in a GitHub profile README via ``<img src="...svg">``.

Artwork note: when an SVG is embedded through an ``<img>`` tag (as GitHub
README images are), the browser sandboxes the SVG and will NOT make external
network requests. External ``<image href="https://...">`` album art therefore
renders blank in the README. The generator embeds artwork as a base64 data
URI (``art_b64``) so the SVG is self-contained and renders everywhere.
``art_url`` is kept only as a hint / for the Last.fm link, never as an
in-SVG image source.

Track dict shape (all fields optional except name/artist):
    name:      str            - track title
    artist:    str            - artist name
    album:     str | None     - album name (optional, not rendered in MVP card)
    art_url:   str | None     - Last.fm CDN url (hint / link only, NOT embedded)
    art_b64:   str | None     - base64 data URI e.g. "data:image/jpeg;base64,...."
    playing:   bool           - True => now playing, False => last played
    played_at: int | None     - unix timestamp of play (for relative time)

The generator never raises on bad input; it always returns a valid SVG.
"""
from __future__ import annotations

import html
import time
from typing import Mapping, Optional

# --- layout constants (viewBox 0 0 480 160) --------------------------------
W, H = 480, 160
PAD = 16
ART = 128  # album art square
ART_R = 8  # art corner radius
TEXT_X = PAD + ART + 18  # 162

# --- palette (GitHub dark default) -----------------------------------------
BG = "#0d1117"
BORDER = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
LABEL_DIM = "#6e7681"
ACCENT_PLAY = "#3fb950"  # GitHub green for "now playing"
PLACEHOLDER_GRAD = ("#30363d", "#21262d")

# rough char caps to keep text inside the card (card text width ~ 300px)
TRACK_MAX = 30
ARTIST_MAX = 34


def _escape(s: str) -> str:
    return html.escape(s, quote=True)


def _ellipsize(s: str, limit: int) -> str:
    s = s.strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "\u2026"


def _relative_time(played_at: Optional[int], now: Optional[int] = None) -> str:
    """Unix ts -> 'just now' / 'N min ago' / 'N hr ago' / 'N d ago'."""
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
    """Album art as self-contained image, or a rounded placeholder block."""
    if art_b64:
        return (
            f'<clipPath id="artclip"><rect x="{PAD}" y="{PAD}" '
            f'width="{ART}" height="{ART}" rx="{ART_R}" ry="{ART_R}"/></clipPath>'
            f'<image x="{PAD}" y="{PAD}" width="{ART}" height="{ART}" '
            f'href="{_escape(art_b64)}" preserveAspectRatio="xMidYMid slice" '
            f'clip-path="url(#artclip)"/>'
        )
    # placeholder: subtle gradient + note glyph
    gid = "artph"
    return (
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{PLACEHOLDER_GRAD[0]}"/>'
        f'<stop offset="1" stop-color="{PLACEHOLDER_GRAD[1]}"/></linearGradient></defs>'
        f'<rect x="{PAD}" y="{PAD}" width="{ART}" height="{ART}" '
        f'rx="{ART_R}" ry="{ART_R}" fill="url(#{gid})"/>'
        f'<text x="{PAD + ART // 2}" y="{PAD + ART // 2 + 8}" '
        f'text-anchor="middle" font-size="40" fill="{BORDER}" '
        'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">&#9835;</text>'
    )


def _fallback_svg(message: str = "Nothing playing yet") -> str:
    """Minimal valid SVG for the empty / error / no-history case."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="{_escape(message)}">'
        f'<rect width="{W}" height="{H}" rx="12" ry="12" fill="{BG}" '
        f'stroke="{BORDER}" stroke-width="1"/>'
        f'<text x="{W // 2}" y="{H // 2}" text-anchor="middle" dominant-baseline="middle" '
        f'fill="{LABEL_DIM}" font-size="14" font-family="-apple-system,BlinkMacSystemFont,'
        f'Segoe UI,sans-serif">{_escape(message)}</text>'
        "</svg>"
    )


def render_svg(track: Optional[Mapping], *, now: Optional[int] = None) -> str:
    """Render a track dict to an SVG string. Always returns valid SVG.

    ``track`` may be ``None`` (empty history / error) => fallback SVG.
    """
    if not track or not track.get("name") or not track.get("artist"):
        return _fallback_svg()

    playing = bool(track.get("playing"))
    name = _ellipsize(str(track.get("name", "")), TRACK_MAX)
    artist = _ellipsize(str(track.get("artist", "")), ARTIST_MAX)
    art_b64 = track.get("art_b64")
    played_at = track.get("played_at")

    label = "NOW PLAYING" if playing else "LAST PLAYED"
    label_color = ACCENT_PLAY if playing else LABEL_DIM
    title_color = TEXT_PRIMARY if playing else TEXT_SECONDARY

    # last played relative time (only when not currently playing)
    sub = ""
    if not playing:
        sub = _relative_time(played_at, now=now)

    art_svg = _art_block(art_b64)

    # optional equalizer hint when playing (static 3 bars; animated in Phase 5)
    eq = ""
    if playing:
        bx = W - PAD - 14
        by = PAD + 2
        bars = [9, 14, 6]
        eq = '<g fill="' + ACCENT_PLAY + '">'
        for i, hgt in enumerate(bars):
            eq += f'<rect x="{bx + i * 5}" y="{by + (14 - hgt)}" width="3" height="{hgt}" rx="1"/>'
        eq += "</g>"

    sub_line = (
        f'<text x="{TEXT_X}" y="110" fill="{LABEL_DIM}" font-size="12" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        f'{_escape(sub)}</text>'
        if sub
        else ""
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="Last.fm: {label} - '
        f'{_escape(name)} by {_escape(artist)}">'
        f'<rect width="{W}" height="{H}" rx="12" ry="12" fill="{BG}" '
        f'stroke="{BORDER}" stroke-width="1"/>'
        f"{art_svg}"
        # clip the whole text column so long names never spill past the card
        f'<clipPath id="tclip"><rect x="{TEXT_X}" y="{PAD}" '
        f'width="{W - TEXT_X - PAD}" height="{H - 2 * PAD}"/></clipPath>'
        f'<g clip-path="url(#tclip)">'
        f'<text x="{TEXT_X}" y="42" fill="{label_color}" font-size="11" '
        f'letter-spacing="1.5" font-weight="600" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        f'{label}</text>'
        f'<text x="{TEXT_X}" y="72" fill="{title_color}" font-size="19" '
        f'font-weight="600" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        f"{_escape(name)}</text>"
        f'<text x="{TEXT_X}" y="96" fill="{TEXT_SECONDARY}" font-size="14" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        f'{_escape(artist)}</text>'
        f"{sub_line}"
        f"</g>"
        f"{eq}"
        "</svg>"
    )
