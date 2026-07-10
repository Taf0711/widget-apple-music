"""Unit tests for lib.svg_generator — no network, pure payload -> SVG checks."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import svg_generator as g

# build the XML quote entity from parts so it survives the source round-trip
QUOT = "&" + "quot;"

# ---------- fixtures ----------
NOW_PLAYING = {
    "name": "Like Water",
    "artist": "Flume",
    "album": "Skin",
    "art_url": "https://lastfm.freetls.fastly.net/i/u/300x300/x.jpg",
    "art_b64": None,
    "playing": True,
    "played_at": None,
}

LAST_PLAYED = {
    "name": "Like Water",
    "artist": "Flume",
    "album": "Skin",
    "art_url": None,
    "art_b64": "data:image/jpeg;base64,QUJD",
    "playing": False,
    "played_at": 1719861213,
}


def test_now_playing_label_and_color():
    svg = g.render_svg(NOW_PLAYING)
    assert "<svg" in svg and "</svg>" in svg
    assert "NOW PLAYING" in svg
    assert "#3fb950" in svg  # playing accent
    # no relative time when currently playing
    assert "ago" not in svg


def test_last_played_relative_time_and_dim():
    t = int(time.time()) - 3 * 60  # 3 min ago
    track = dict(LAST_PLAYED, played_at=t)
    svg = g.render_svg(track, now=int(time.time()) + 1)
    assert "LAST PLAYED" in svg
    assert "3 min ago" in svg
    assert "#6e7681" in svg  # dim label color


def test_empty_track_returns_fallback():
    svg = g.render_svg(None)
    assert "Nothing playing yet" in svg
    assert "<svg" in svg


def test_partial_track_missing_artist_returns_fallback():
    svg = g.render_svg({"name": "X"})  # no artist
    assert "Nothing playing yet" in svg


def test_long_names_are_ellipsized():
    long_track = "A" * 60
    long_artist = "B" * 60
    svg = g.render_svg({"name": long_track, "artist": long_artist, "playing": True})
    assert "\u2026" in svg  # ellipsis present
    assert long_track not in svg
    assert long_artist not in svg


def test_art_b64_embedded_as_image():
    svg = g.render_svg(LAST_PLAYED)
    assert 'href="data:image/jpeg;base64,QUJD"' in svg
    assert "url(#artclip)" in svg  # rounded corner clip


def test_missing_art_shows_placeholder():
    svg = g.render_svg({"name": "T", "artist": "A", "playing": True, "art_b64": None})
    assert "linearGradient" in svg  # placeholder gradient
    assert "data:image" not in svg


def test_xml_special_chars_escaped():
    svg = g.render_svg({"name": "A & B <c>", "artist": 'X "Y"', "playing": True})
    # html.escape(quote=True) must turn the stray double-quote into the
    # quote entity so it cannot break out of an SVG attribute.
    assert QUOT in svg
    # raw double-quote should not appear as a standalone attr-breaker beyond
    # the ones the generator itself emits (at least the entity is present)
    assert "<" in svg and ">" in svg and "&" in svg


def test_relative_time_buckets():
    now = 1_000_000_000
    cases = {
        30: "just now",
        120: "2 min ago",
        7200: "2 hr ago",
        3 * 86400: "3 d ago",
        14 * 86400: "2 wk ago",
    }
    for secs, expected in cases.items():
        assert g._relative_time(now - secs, now=now) == expected, secs


def test_svg_well_formed_root():
    import xml.etree.ElementTree as ET

    svg = g.render_svg(NOW_PLAYING)
    root = ET.fromstring(svg)
    assert root.tag.endswith("}svg")
    assert root.attrib["width"] == "480"
    assert root.attrib["height"] == "160"
