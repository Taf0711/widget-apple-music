"""Last.fm API client — parse track data, fetch recent tracks, fetch album art.

All public functions use only the Python standard library (urllib, json, base64).
No third-party dependencies.
"""

import base64
import json
import urllib.parse
import urllib.request


class LastfmError(Exception):
    """Raised when the Last.fm API returns an error response or a network error occurs."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self):
        if self.code is not None:
            return f"[{self.code}] {self.message}"
        return self.message


def parse_track(data: dict) -> dict | None:
    """Parse a Last.fm user.getrecenttracks JSON dict into a track dict.

    Returns None when there is no track data (empty history, missing keys, etc.).
    Raises LastfmError if *data* contains an ``'error'`` key.
    Never raises a raw KeyError, TypeError, or IndexError on unexpected input.
    """
    if not isinstance(data, dict):
        return None

    # API error response
    if "error" in data:
        code = int(data["error"])
        message = data.get("message", "")
        raise LastfmError(message, code=code)

    # Navigate to the track list
    try:
        recenttracks = data.get("recenttracks")
        if not isinstance(recenttracks, dict):
            return None
    except Exception:
        return None

    raw_track = recenttracks.get("track")
    if raw_track is None:
        return None

    # The API may return a list of tracks or a single dict
    if isinstance(raw_track, dict):
        tracks = [raw_track]
    elif isinstance(raw_track, list):
        tracks = raw_track
    else:
        return None

    if not tracks:
        return None

    track = tracks[0]
    if not isinstance(track, dict):
        return None

    # --- extract fields (safe access only) ---

    # name
    name = track.get("name")
    if not isinstance(name, str):
        return None

    # artist
    artist_obj = track.get("artist")
    if isinstance(artist_obj, dict):
        artist = artist_obj.get("#text")
    else:
        artist = None
    if not isinstance(artist, str):
        return None

    # album
    album_obj = track.get("album")
    if isinstance(album_obj, dict):
        album = album_obj.get("#text")
    else:
        album = None
    # album may be an empty string; normalise to None
    if not album:
        album = None

    # art_url (extralarge image)
    art_url = None
    images = track.get("image")
    if isinstance(images, list):
        for img in images:
            if isinstance(img, dict) and img.get("size") == "extralarge":
                url = img.get("#text")
                if url:
                    art_url = url
                break

    # playing
    playing = False
    attr = track.get("@attr")
    if isinstance(attr, dict) and attr.get("nowplaying") == "true":
        playing = True

    # played_at
    played_at = None
    date_obj = track.get("date")
    if isinstance(date_obj, dict):
        uts = date_obj.get("uts")
        if uts is not None:
            try:
                played_at = int(uts)
            except (ValueError, TypeError):
                pass

    return {
        "name": name,
        "artist": artist,
        "album": album,
        "art_url": art_url,
        "art_b64": None,
        "playing": playing,
        "played_at": played_at,
    }


def fetch_recent_tracks(username, api_key, *, limit=1, timeout=5) -> dict:
    """Fetch recent tracks from the Last.fm API over HTTP.

    Returns the parsed JSON dict.
    Raises LastfmError on API errors or network / JSON decode failures.
    """
    params = {
        "method": "user.getrecenttracks",
        "user": username,
        "api_key": api_key,
        "format": "json",
        "limit": limit,
    }
    url = "https://ws.audioscrobbler.com/2.0/?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except Exception as exc:
        raise LastfmError(message=str(exc), code=None) from exc

    try:
        data = json.loads(body)
    except Exception as exc:
        raise LastfmError(message=str(exc), code=None) from exc

    if isinstance(data, dict) and "error" in data:
        code = int(data["error"])
        message = data.get("message", "")
        raise LastfmError(message=message, code=code)

    return data


def get_now_playing(username, api_key, *, limit=1, timeout=5) -> dict | None:
    """Fetch the most recent track and parse it into a track dict.

    Returns the track dict or None on empty history.
    """
    data = fetch_recent_tracks(username, api_key, limit=limit, timeout=timeout)
    return parse_track(data)


def fetch_art_b64(url, *, timeout=5) -> str | None:
    """Fetch album art from *url* and return a base64 data URI.

    Returns ``data:image/png;base64,...`` or ``data:image/jpeg;base64,...``.
    Returns None if *url* is empty/falsy or on any network error.
    """
    if not url:
        return None

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            info = resp.info()

        # Determine content type
        content_type = "image/jpeg"
        if hasattr(info, "get_content_type"):
            raw_ct = info.get_content_type()
            if raw_ct == "image/png":
                content_type = "image/png"
        elif isinstance(info, dict):
            raw_ct = info.get("Content-Type", "")
            if raw_ct == "image/png":
                content_type = "image/png"

        b64_str = base64.b64encode(raw).decode("ascii")
        return f"data:{content_type};base64,{b64_str}"
    except Exception:
        return None
