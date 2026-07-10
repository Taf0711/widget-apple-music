"""Vercel serverless function: Last.fm -> self-contained now-playing SVG.

Route: GET /api/now-playing?user=NAME
Returns: 200 image/svg+xml  (always 200, even on error -> a fallback SVG so the
        README image never breaks)

Env:     LASTFM_API_KEY  (set in the Vercel project dashboard / vercel env)

Uses only the Python standard library + the two local lib modules.
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
import sys
import traceback
from pathlib import Path

# make lib/ importable on Vercel (entrypoint lives in api/)
_LIB = str(Path(__file__).resolve().parent.parent / "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import lastfm  # noqa: E402
import svg_generator  # noqa: E402

# cache: GitHub caches images; keep edge + browser fresh-ish but bounded
CACHE_HDR = "public, s-maxage=60, max-age=60"


def serve(user, api_key):
    """Core logic, factored out so it's testable without a live Vercel request.

    Returns (status:int, content_type:str, body:bytes).
    Always returns a valid SVG body (fallback on any failure).
    """
    if not user:
        body = svg_generator.render_svg(None).encode("utf-8")
        return 200, "image/svg+xml", body  # empty-state SVG, not a hard 400

    if not api_key:
        body = svg_generator.render_svg(None).encode("utf-8")
        return 200, "image/svg+xml", body  # misconfig -> graceful fallback

    try:
        track = lastfm.get_now_playing(user, api_key)
        if track and track.get("art_url"):
            track["art_b64"] = lastfm.fetch_art_b64(track["art_url"])
        body = svg_generator.render_svg(track).encode("utf-8")
        return 200, "image/svg+xml", body
    except lastfm.LastfmError:
        # user not found / rate limit / api down -> fallback, not a broken image
        body = svg_generator.render_svg(None).encode("utf-8")
        return 200, "image/svg+xml", body
    except Exception:  # noqa: BLE001 - never let the README image 500
        traceback.print_exc()
        body = svg_generator.render_svg(None).encode("utf-8")
        return 200, "image/svg+xml", body


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        user = (query.get("user", [None])[0] or "").strip() or None
        api_key = os.environ.get("LASTFM_API_KEY")

        status, ctype, body = serve(user, api_key)

        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", CACHE_HDR)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence Vercel's default request logging
        pass
