"""Render hardcoded sample payloads to sample_*.svg so they can be opened in
a browser to visually verify the widget design. No network.

Usage:
    python3 scripts/render_sample.py
    open sample_now_playing.svg sample_last_played.svg sample_empty.svg
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import svg_generator as g

NOW_PLAYING = {
    "name": "Like Water",
    "artist": "Flume",
    "album": "Skin",
    "art_b64": None,  # placeholder art (no real image on disk for the sample)
    "playing": True,
    "played_at": None,
}

LAST_PLAYED = {
    "name": "The Less I Know The Better",
    "artist": "Tame Impala",
    "album": "Currents",
    "art_b64": None,
    "playing": False,
    "played_at": int(time.time()) - 3 * 60,  # 3 min ago, for a realistic demo
}


def main() -> None:
    out = Path(__file__).resolve().parent.parent
    cases = {
        "sample_now_playing.svg": NOW_PLAYING,
        "sample_last_played.svg": LAST_PLAYED,
        "sample_empty.svg": None,
    }
    for fname, track in cases.items():
        svg = g.render_svg(track)
        (out / fname).write_text(svg, encoding="utf-8")
        print(f"wrote {fname} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
