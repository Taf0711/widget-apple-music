"""Embedded-style terminal header — phosphor text on transparent, no window frame.

Loses the CRT bezel/scanlines but keeps the glow + typewriter. Blends into
GitHub's dark background like it's text on the page. Best for minimal profiles
that want the terminal *feel* without the "app window" look.
"""
from __future__ import annotations

import html

# Compact dimensions — just the text line, no chrome
W = 560
H = 40
FONT_SIZE = 16
CHAR_W = FONT_SIZE * 0.62
BASELINE_Y = H // 2 + 2
PROMPT = "> "
TEXT_X = len(PROMPT) * CHAR_W + 8

# GitHub dark + phosphor
PHOSPHOR = "#33ff66"
PHOSPHOR_DIM = "#1a9940"
TEXT_PRIMARY = "#e6edf3"

FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

PHRASES = [
    "Hi, my name is Tafseer Haque",
    "I like to build ambitious things",
]

TYPE_MS = 55
PAUSE_MS = 1600
ERASE_MS = 30
GAP_MS = 400


def _escape(s: str) -> str:
    return html.escape(s, quote=True)


def _timeline(n: int) -> tuple[list[float], list[int], int]:
    if n == 0:
        return [0.0, 0.0], [GAP_MS], GAP_MS
    full = n * CHAR_W
    widths = [i * CHAR_W for i in range(n + 1)]
    widths += [full]
    widths += [i * CHAR_W for i in range(n - 1, -1, -1)]
    widths += [0.0]
    segs = [TYPE_MS] * n + [PAUSE_MS] + [ERASE_MS] * n + [GAP_MS]
    assert len(segs) == len(widths) - 1
    return widths, segs, sum(segs)


def _key_times(segs: list[int]) -> str:
    total = float(sum(segs))
    acc = 0.0
    out = ["0"]
    for w in segs:
        acc += w
        out.append(f"{min(acc / total, 1.0):.4f}")
    return ";".join(out)


def _phrase_block(phrase: str, idx: int, n_phrases: int) -> tuple[str, str]:
    widths, segs, dur = _timeline(len(phrase))
    keytimes = _key_times(segs)

    def d_at(w: float) -> str:
        return f"M{TEXT_X:.1f},{BASELINE_Y} h{max(w, 0.01):.1f}"

    values = ";".join(d_at(w) for w in widths)
    cursor_xs = ";".join(f"{TEXT_X + w:.1f}" for w in widths)
    begin = f"0s;a{n_phrases - 1}.end" if idx == 0 else f"a{idx - 1}.end"
    pid, aid = f"p{idx}", f"a{idx}"

    path = (
        f"<path id='{pid}' d='{d_at(0)}' fill='none'>"
        f"<animate id='{aid}' attributeName='d' begin='{begin}' "
        f"dur='{dur}ms' fill='freeze' calcMode='discrete' "
        f"values='{values}' keyTimes='{keytimes}'/>"
        f"</path>"
        f"<text font-family='{FONT}' fill='{PHOSPHOR}' font-size='{FONT_SIZE}' "
        f"font-weight='500' dominant-baseline='middle' "
        f"filter='url(#glow)'>"
        f"<textPath href='#{pid}' xlink:href='#{pid}' startOffset='0'>"
        f"{_escape(phrase)}</textPath></text>"
    )
    cur = (
        f"<animate attributeName='x' begin='{begin}' "
        f"dur='{dur}ms' fill='freeze' calcMode='discrete' "
        f"values='{cursor_xs}' keyTimes='{keytimes}'/>"
    )
    return path, cur


def render_terminal_svg() -> str:
    paths: list[str] = []
    cursors: list[str] = []
    for i, phrase in enumerate(PHRASES):
        p, c = _phrase_block(phrase, i, len(PHRASES))
        paths.append(p)
        cursors.append(c)

    # subtle glow filter
    glow = (
        "<defs>"
        "<filter id='glow' x='-20%' y='-40%' width='140%' height='180%' "
        "color-interpolation-filters='sRGB'>"
        "<feGaussianBlur in='SourceGraphic' stdDeviation='1.2' result='b'/>"
        "<feMerge><feMergeNode in='b'/><feMergeNode in='SourceGraphic'/></feMerge>"
        "</filter>"
        "</defs>"
    )

    prompt = (
        f"<text x='8' y='{BASELINE_Y}' font-family='{FONT}' "
        f"font-size='{FONT_SIZE}' font-weight='600' fill='{PHOSPHOR_DIM}' "
        f"dominant-baseline='middle' filter='url(#glow)'>"
        f"{_escape(PROMPT)}</text>"
    )

    cursor = (
        f"<rect x='{TEXT_X:.1f}' y='{BASELINE_Y - 10}' width='8' "
        f"height='14' fill='{PHOSPHOR}' rx='1' filter='url(#glow)'>"
        f"{''.join(cursors)}"
        f"<animate attributeName='opacity' values='1;1;0.2;0.2' "
        f"keyTimes='0;0.55;0.6;1' dur='1.05s' repeatCount='indefinite'/>"
        f"</rect>"
    )

    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' "
        f"xmlns:xlink='http://www.w3.org/1999/xlink' "
        f"width='{W}' height='{H}' viewBox='0 0 {W} {H}' role='img' "
        f"aria-label='Terminal: Tafseer Haque'>"
        f"{glow}"
        # NO background rect — transparent
        f"{prompt}{''.join(paths)}{cursor}"
        f"</svg>"
    )


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "terminal_embedded.svg"
    svg = render_terminal_svg()
    open(out, "w").write(svg)
    print(f"wrote {out} ({len(svg)} bytes)")
