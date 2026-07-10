"""Unit tests for lib.svg_generator (v2 design) — no network."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import svg_generator as g

QUOT = "&" + "quot;"  # build the XML quote entity from parts (survives source round-trip)

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


def test_now_playing_label_color_and_equalizer():
    svg = g.render_svg(NOW_PLAYING)
    assert "<svg" in svg and "</svg>" in svg
    assert "NOW PLAYING" in svg
    assert "#3fb950" in svg              # green accent
    assert 'class="eq-bar' in svg        # equalizer bars present
    assert "eqbounce" in svg             # bounce keyframes present
    assert "scaleY" in svg               # scales vertically
    assert "ago" not in svg             # no relative time


def test_last_played_has_no_label_no_time_no_equalizer():
    svg = g.render_svg(LAST_PLAYED)
    assert "LAST PLAYED" not in svg
    assert "NOW PLAYING" not in svg
    assert "ago" not in svg
    assert 'class="eq-bar' not in svg   # no equalizer when not playing
    assert "#8b949e" in svg              # dimmed title color


def test_equalizer_has_four_bars():
    svg = g.render_svg(NOW_PLAYING)
    assert svg.count('class="eq-bar') == g.EQ_COUNT  # exactly 4 bars


def test_empty_track_returns_fallback():
    svg = g.render_svg(None)
    assert "Nothing playing yet" in svg
    assert "<svg" in svg


def test_partial_track_missing_artist_returns_fallback():
    svg = g.render_svg({"name": "X"})
    assert "Nothing playing yet" in svg


def test_long_names_are_ellipsized():
    long_track = "A" * 60
    long_artist = "B" * 60
    svg = g.render_svg({"name": long_track, "artist": long_artist, "playing": True})
    assert "\u2026" in svg
    assert long_track not in svg
    assert long_artist not in svg


def test_art_b64_embedded_as_image():
    svg = g.render_svg(LAST_PLAYED)
    assert 'href="data:image/jpeg;base64,QUJD"' in svg
    assert "url(#artclip)" in svg


def test_missing_art_shows_placeholder():
    svg = g.render_svg({"name": "T", "artist": "A", "playing": True, "art_b64": None})
    assert "linearGradient" in svg
    assert "data:image" not in svg


def test_xml_special_chars_escaped():
    svg = g.render_svg({"name": "A & B <c>", "artist": 'X "Y"', "playing": True})
    assert QUOT in svg
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


def test_svg_well_formed_root_and_size():
    import xml.etree.ElementTree as ET

    svg = g.render_svg(NOW_PLAYING)
    root = ET.fromstring(svg)
    assert root.tag.endswith("}svg")
    assert root.attrib["width"] == "400"
    assert root.attrib["height"] == "84"
