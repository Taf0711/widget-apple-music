"""Embedded-style now-playing SVG — no card, blends into GitHub's UI.

Transparent background, GitHub's native colors, no border. The widget looks
like text on the page, not an image box. Best for profiles that want a
minimal, native feel.

Tradeoff: loses the "app window" look. The equalizer and label still animate.
"""
from __future__ import annotations

import html
import time
from typing import Mapping, Optional

# GitHub dark mode colors (exact)
TEXT_PRIMARY = "#e6edf3"      # primary text
TEXT_SECONDARY = "#8b949e"    # secondary text
TEXT_TERTIARY = "#6e7681"     # muted/label text
ACCENT = "#3fb950"            # GitHub green
ACCENT_DIM = "#2ea043"        # dimmed green
ART_PLACEHOLDER = "#30363d"   # subtle dark

# Layout — compact, text-only (no card)
W, H = 320, 64
ART_SIZE = 48
ART_X = 0
ART_Y = (H - ART_SIZE) // 2
TEXT_X = ART_SIZE + 12
FONT_MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
FONT_SANS = "-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans,Helvetica,Arial,sans-serif"

TRACK_MAX = 24
ARTIST_MAX = 26


def _escape(s: str) -> str:
    return html.escape(s, quote=True)


def _ellipsize(s: str, limit: int) -> str:
    s = s.strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "…"


def _relative_time(played_at: Optional[int], now: Optional[int] = None) -> str:
    if not played_at:
        return ""
    now = int(now if now is not None else time.time())
    secs = max(0, now - int(played_at))
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    days = secs // 86400
    return f"{days}d ago"


def _art_block(art_b64: Optional[str]) -> str:
    """Album art or a subtle placeholder dot."""
    if art_b64:
        return (
            f'<clipPath id="artclip"><rect x="{ART_X}" y="{ART_Y}" '
            f'width="{ART_SIZE}" height="{ART_SIZE}" rx="4" ry="4"/></clipPath>'
            f'<image x="{ART_X}" y="{ART_Y}" width="{ART_SIZE}" height="{ART_SIZE}" '
            f'href="{_escape(art_b64)}" preserveAspectRatio="xMidYMid slice" '
            f'clip-path="url(#artclip)"/>'
        )
    # placeholder: subtle dark square, no emoji
    return (
        f'<rect x="{ART_X}" y="{ART_Y}" width="{ART_SIZE}" height="{ART_SIZE}" '
        f'rx="4" ry="4" fill="{ART_PLACEHOLDER}"/>'
        f'<circle cx="{ART_X + ART_SIZE // 2}" cy="{ART_Y + ART_SIZE // 2}" '
        f'r="6" fill="{TEXT_TERTIARY}"/>'
    )


def _equalizer(playing: bool) -> str:
    """3 small bars when playing."""
    if not playing:
        return ""
    bars = ""
    base_y = 40
    for i, (h, dur) in enumerate([(8, "0.9s"), (12, "0.7s"), (6, "1.1s")]):
        x = TEXT_X + i * 5
        bars += (
            f'<rect x="{x}" y="{base_y - h}" width="3" height="{h}" '
            f'rx="1" fill="{ACCENT}" opacity="0.8">'
            f'<animate attributeName="height" values="{h};{h//2};{h}" '
            f'dur="{dur}" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{base_y - h};{base_y - h//2};{base_y - h}" '
            f'dur="{dur}" repeatCount="indefinite"/>'
            f'</rect>'
        )
    return bars


def render_svg(track: Optional[Mapping], *, now: Optional[int] = None) -> str:
    """Render track as embedded-style SVG (transparent, no card)."""
    if not track or not track.get("name") or not track.get("artist"):
        return _fallback_svg()

    playing = bool(track.get("playing"))
    name = _ellipsize(str(track.get("name", "")), TRACK_MAX)
    artist = _ellipsize(str(track.get("artist", "")), ARTIST_MAX)
    art_b64 = track.get("art_b64")
    played_at = track.get("played_at")

    # label
    if playing:
        label = "now playing"
        label_color = ACCENT
    else:
        rel = _relative_time(played_at, now)
        label = f"last played · {rel}" if rel else "last played"
        label_color = ACCENT_DIM

    art_svg = _art_block(art_b64)
    eq_svg = _equalizer(playing)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Last.fm {label}: {_escape(name)} by {_escape(artist)}">'
        # NO background rect — transparent, blends into page
        f"{art_svg}"
        f'<text x="{TEXT_X}" y="20" fill="{label_color}" font-size="9" '
        f'font-weight="600" letter-spacing="0.5" '
        f'font-family="{FONT_SANS}">{label.upper()}</text>'
        f'<text x="{TEXT_X}" y="38" fill="{TEXT_PRIMARY}" font-size="13" '
        f'font-weight="600" font-family="{FONT_SANS}">{_escape(name)}</text>'
        f'<text x="{TEXT_X}" y="54" fill="{TEXT_SECONDARY}" font-size="11" '
        f'font-family="{FONT_SANS}">{_escape(artist)}</text>'
        f"{eq_svg}"
        "</svg>"
    )


def _fallback_svg(message: str = "nothing playing") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="{_escape(message)}">'
        f'<text x="0" y="{H // 2}" fill="{TEXT_TERTIARY}" font-size="11" '
        f'font-family="{FONT_SANS}" dominant-baseline="middle">'
        f'{_escape(message)}</text>'
        "</svg>"
    )


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "embedded.svg"
    track = {
        "name": "Like Water",
        "artist": "Flume",
        "album": "Skin",
        "art_url": None,
        "art_b64": None,
        "playing": True,
        "played_at": None,
    }
    svg = render_svg(track)
    open(out, "w").write(svg)
    print(f"wrote {out} ({len(svg)} bytes)")
