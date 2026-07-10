"""Unit tests for the serverless handler's serve() core — no network, no Vercel."""
import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

# api/now-playing.py has a hyphen in the name -> load via importlib
_spec = importlib.util.spec_from_file_location(
    "now_playing_handler", ROOT / "api" / "now-playing.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)
serve = mod.serve

import lastfm  # noqa: E402  (for the LastfmError type + mocking target)


TRACK = {
    "name": "Like Water",
    "artist": "Flume",
    "album": "Skin",
    "art_url": "https://x/a.png",
    "art_b64": None,
    "playing": True,
    "played_at": None,
}


def test_no_user_returns_fallback_svg():
    status, ctype, body = serve(None, "KEY")
    assert status == 200
    assert ctype == "image/svg+xml"
    assert b"Nothing playing yet" in body


def test_no_api_key_returns_fallback_svg():
    status, ctype, body = serve("L03ST", None)
    assert status == 200
    assert b"Nothing playing yet" in body


def test_track_rendered_with_art():
    with patch("lastfm.get_now_playing", return_value=TRACK), patch(
        "lastfm.fetch_art_b64", return_value="data:image/png;base64,QUJD"
    ):
        status, ctype, body = serve("L03ST", "KEY")
    assert status == 200
    assert ctype == "image/svg+xml"
    assert b"NOW PLAYING" in body
    assert b"Like Water" in body


def test_empty_history_returns_fallback_svg():
    with patch("lastfm.get_now_playing", return_value=None):
        status, ctype, body = serve("L03ST", "KEY")
    assert status == 200
    assert b"Nothing playing yet" in body


def test_lastfm_error_returns_fallback_not_500():
    with patch("lastfm.get_now_playing", side_effect=lastfm.LastfmError("User not found", code=6)):
        status, ctype, body = serve("bad", "KEY")
    assert status == 200  # graceful fallback, never a broken image
    assert b"Nothing playing yet" in body


def test_unexpected_exception_returns_fallback_not_500():
    with patch("lastfm.get_now_playing", side_effect=RuntimeError("boom")):
        status, ctype, body = serve("L03ST", "KEY")
    assert status == 200
    assert b"Nothing playing yet" in body
