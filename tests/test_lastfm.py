"""Unit tests for lib.lastfm — no real network (all mocked).

The contract: parse_track turns a user.getrecenttracks JSON dict into the
track-dict shape consumed by lib.svg_generator, or None for empty history,
and raises LastfmError on API error responses. fetch_* are thin network
wrappers tested via monkeypatched urlopen.
"""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import lastfm


# ---------- real-shaped fixtures (captured from the live API) ----------
NOW_PLAYING_PAYLOAD = {
    "recenttracks": {
        "track": [
            {
                "artist": {"mbid": "x", "#text": "Flume"},
                "streamable": "0",
                "image": [
                    {"size": "small", "#text": "https://lastfm.freetls.fastly.net/i/u/34s/a.png"},
                    {"size": "medium", "#text": "https://lastfm.freetls.fastly.net/i/u/64s/a.png"},
                    {"size": "large", "#text": "https://lastfm.freetls.fastly.net/i/u/174s/a.png"},
                    {"size": "extralarge", "#text": "https://lastfm.freetls.fastly.net/i/u/300x300/a.png"},
                ],
                "mbid": "y",
                "album": {"mbid": "z", "#text": "Skin"},
                "name": "Like Water",
                "url": "https://www.last.fm/music/Flume/_/Like+Water",
                "@attr": {"nowplaying": "true"},
            }
        ],
        "@attr": {"user": "L03ST", "totalPages": "1", "page": "1", "perPage": "1", "total": "1"},
    }
}

LAST_PLAYED_PAYLOAD = {
    "recenttracks": {
        "track": [
            {
                "artist": {"mbid": "x", "#text": "Tame Impala"},
                "image": [
                    {"size": "extralarge", "#text": "https://lastfm.freetls.fastly.net/i/u/300x300/b.jpg"},
                    {"size": "small", "#text": "https://lastfm.freetls.fastly.net/i/u/34s/b.jpg"},
                ],
                "album": {"mbid": "z", "#text": "Currents"},
                "name": "The Less I Know The Better",
                "url": "https://www.last.fm/music/Tame+Impala/_/The+Less+I+Know+The+Better",
                "date": {"uts": "1719861213", "#text": "01 Jul 2024, 12:33"},
            }
        ],
        "@attr": {"user": "L03ST", "totalPages": "1", "page": "1", "perPage": "1", "total": "1"},
    }
}

EMPTY_PAYLOAD = {
    "recenttracks": {
        "track": [],
        "@attr": {"user": "L03ST", "totalPages": "0", "page": "1", "perPage": "1", "total": "0"},
    }
}

# defensive: single track returned as a dict, not a list (classic Last.fm quirk)
SINGLE_DICT_QUIRK = {
    "recenttracks": {
        "track": {
            "artist": {"#text": "Aphex Twin"},
            "image": [{"size": "extralarge", "#text": "https://x/300x300/c.png"}],
            "album": {"#text": "Selected Ambient Works"},
            "name": "Xtal",
            "date": {"uts": "1700000000", "#text": "old"},
        }
    }
}

ERROR_USER_NOT_FOUND = {"error": 6, "message": "User not found"}
ERROR_INVALID_KEY = {"error": 10, "message": "Invalid API key - You must be granted a valid key by last.fm"}

# track missing album + all images
MISSING_FIELDS = {
    "recenttracks": {
        "track": [
            {
                "artist": {"#text": "Unknown Artist"},
                "image": [],
                "name": "Mystery Track",
                "date": {"uts": "1700000000", "#text": "old"},
            }
        ]
    }
}


# ---------- parse_track ----------
def test_parse_now_playing():
    t = lastfm.parse_track(NOW_PLAYING_PAYLOAD)
    assert t is not None
    assert t["name"] == "Like Water"
    assert t["artist"] == "Flume"
    assert t["album"] == "Skin"
    assert t["playing"] is True
    assert t["played_at"] is None
    assert t["art_url"] == "https://lastfm.freetls.fastly.net/i/u/300x300/a.png"
    assert t["art_b64"] is None  # filled by the serverless fn, not the parser


def test_parse_last_played():
    t = lastfm.parse_track(LAST_PLAYED_PAYLOAD)
    assert t is not None
    assert t["name"] == "The Less I Know The Better"
    assert t["artist"] == "Tame Impala"
    assert t["playing"] is False
    assert t["played_at"] == 1719861213
    assert t["art_url"] == "https://lastfm.freetls.fastly.net/i/u/300x300/b.jpg"


def test_parse_empty_returns_none():
    assert lastfm.parse_track(EMPTY_PAYLOAD) is None


def test_parse_single_dict_quirk():
    t = lastfm.parse_track(SINGLE_DICT_QUIRK)
    assert t is not None
    assert t["name"] == "Xtal"
    assert t["artist"] == "Aphex Twin"
    assert t["playing"] is False
    assert t["played_at"] == 1700000000


def test_parse_missing_fields_graceful():
    t = lastfm.parse_track(MISSING_FIELDS)
    assert t is not None
    assert t["name"] == "Mystery Track"
    assert t["artist"] == "Unknown Artist"
    assert t["album"] is None
    assert t["art_url"] is None


def test_parse_error_user_not_found_raises():
    with pytest.raises(lastfm.LastfmError) as exc:
        lastfm.parse_track(ERROR_USER_NOT_FOUND)
    assert exc.value.code == 6


def test_parse_error_invalid_key_raises():
    with pytest.raises(lastfm.LastfmError) as exc:
        lastfm.parse_track(ERROR_INVALID_KEY)
    assert exc.value.code == 10


def test_parse_garbage_returns_none_or_raises_clean():
    # totally unexpected shape -> None (never raise a raw KeyError/TypeError)
    assert lastfm.parse_track({}) is None
    assert lastfm.parse_track({"recenttracks": {}}) is None


# ---------- fetch_recent_tracks (network, mocked) ----------
def _mock_response(body: bytes):
    m = MagicMock()
    m.read.return_value = body
    m.__enter__ = lambda self: self
    m.__exit__ = lambda *a: None
    return m


def test_fetch_recent_tracks_builds_url_and_returns_json():
    body = json.dumps(LAST_PLAYED_PAYLOAD).encode()
    with patch("urllib.request.urlopen", return_value=_mock_response(body)) as u:
        data = lastfm.fetch_recent_tracks("L03ST", "KEY123", limit=1)
    assert data == LAST_PLAYED_PAYLOAD
    called_url = u.call_args[0][0].get_full_url() if hasattr(u.call_args[0][0], "get_full_url") else str(u.call_args[0][0])
    assert "method=user.getrecenttracks" in called_url
    assert "user=L03ST" in called_url
    assert "api_key=KEY123" in called_url
    assert "format=json" in called_url


def test_fetch_recent_tracks_raises_on_api_error_response():
    body = json.dumps(ERROR_USER_NOT_FOUND).encode()
    with patch("urllib.request.urlopen", return_value=_mock_response(body)):
        with pytest.raises(lastfm.LastfmError) as exc:
            lastfm.fetch_recent_tracks("bad", "KEY123")
    assert exc.value.code == 6


def test_get_now_playing_end_to_end_mocked():
    body = json.dumps(NOW_PLAYING_PAYLOAD).encode()
    with patch("urllib.request.urlopen", return_value=_mock_response(body)):
        t = lastfm.get_now_playing("L03ST", "KEY123")
    assert t is not None and t["playing"] is True and t["name"] == "Like Water"


def test_get_now_playing_empty_mocked():
    body = json.dumps(EMPTY_PAYLOAD).encode()
    with patch("urllib.request.urlopen", return_value=_mock_response(body)):
        assert lastfm.get_now_playing("L03ST", "KEY123") is None


# ---------- fetch_art_b64 (network, mocked) ----------
def test_fetch_art_b64_returns_data_uri():
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20  # fake png header + padding
    m = _mock_response(png_bytes)
    m.info.return_value = {"Content-Type": "image/png"}
    with patch("urllib.request.urlopen", return_value=m):
        uri = lastfm.fetch_art_b64("https://x/a.png")
    assert uri is not None
    assert uri.startswith("data:image/png;base64,")
    assert len(uri) > len("data:image/png;base64,")


def test_fetch_art_b64_none_on_failure():
    with patch("urllib.request.urlopen", side_effect=OSError("boom")):
        assert lastfm.fetch_art_b64("https://x/a.png") is None


def test_fetch_art_b64_none_for_empty_url():
    assert lastfm.fetch_art_b64("") is None
    assert lastfm.fetch_art_b64(None) is None
