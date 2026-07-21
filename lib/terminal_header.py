"""CRT / Fallout-style terminal header for the GitHub profile README.

60s–80s monochrome phosphor locked to a RobCo-style termlink:
  header strip → `>` prompt → teletype reveal → block caret on the caret cell.

No macOS traffic lights. No chrome that didn't exist on a glass tube.

Technique: SMIL animates each phrase path's width; text on a <textPath> so
clipping = typewriter. calcMode=discrete = per-char pops. Base path empty +
fill=freeze so phrases never stack. Phosphor glow via feGaussianBlur (inline
filter, works when the SVG is loaded as an image).

Self-contained. No deps.
"""
from __future__ import annotations

import html

# --- tube geometry --------------------------------------------------------
W, H = 680, 88
BEZEL = 2
# content inset inside the curved faceplate illusion
INSET_X = 18
HEADER_Y = 22
RULE_Y = 32
LINE_Y = 58          # typing baseline
# monospace cell — slightly wide so glyph + caret clear each other
FONT_SIZE = 17
CHAR_W = FONT_SIZE * 0.62
PROMPT = "> "
PROMPT_W = len(PROMPT) * CHAR_W
TEXT_X = INSET_X + PROMPT_W
CURSOR_W = CHAR_W * 0.85
CURSOR_H = FONT_SIZE + 2
CURSOR_Y = LINE_Y - CURSOR_H + 4

# --- phosphor palette (P1 green-ish, Fallout-adjacent) --------------------
BG = "#020803"            # residual dark glass, not pure black
FACE = "#041006"          # inner screen fill
PHOSPHOR = "#33ff66"      # hot green core
PHOSPHOR_DIM = "#1a9940"  # cooled phosphor / header
PHOSPHOR_GLOW = "#22cc55"
PHOSPHOR_FAINT = "#0a3d18"
AMBER_HINT = "#9fff9f"    # near-white green peak for caret
BORDER = "#0d2818"
SCAN = "#000000"

FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,Lucida Console,monospace"

# system chrome (ALWAYS CAPS — real termlink firmware)
HEADER = "ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL"
# the human lines keep normal case so the name reads as a name
PHRASES = [
    "Hi, my name is Tafseer Haque",
    "I like to build ambitious things",
]

# teletype cadence — closer to a serial terminal than a IDE feature
TYPE_MS = 70       # ~14 cps; ASR-33 was ~10, glass TTYs faster
PAUSE_MS = 1800
ERASE_MS = 35
GAP_MS = 450
START_DELAY = 0.6  # bare primed screen before first keystroke


def _escape(s: str) -> str:
    return html.escape(s, quote=True)


def _timeline(n: int) -> tuple[list[float], list[int], int]:
    """(widths, segment_ms, duration_ms). Discrete holds values[i] until next keyTime."""
    if n == 0:
        return [0.0, 0.0], [GAP_MS], GAP_MS
    full = n * CHAR_W
    widths = [i * CHAR_W for i in range(n + 1)]          # type 0..n
    widths += [full]                                      # pause hold
    widths += [i * CHAR_W for i in range(n - 1, -1, -1)]  # erase n-1..0
    widths += [0.0]                                       # empty gap hold
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


def _filters() -> str:
    # phosphor bloom + a soft radial vignette used by the faceplate
    return (
        "<defs>"
        "<filter id='glow' x='-20%' y='-40%' width='140%' height='180%' "
        "color-interpolation-filters='sRGB'>"
        "<feGaussianBlur in='SourceGraphic' stdDeviation='1.6' result='b'/>"
        "<feMerge><feMergeNode in='b'/><feMergeNode in='b'/>"
        "<feMergeNode in='SourceGraphic'/></feMerge>"
        "</filter>"
        "<filter id='soft' x='-10%' y='-10%' width='120%' height='120%' "
        "color-interpolation-filters='sRGB'>"
        "<feGaussianBlur in='SourceGraphic' stdDeviation='0.6'/>"
        "</filter>"
        "<radialGradient id='vignette' cx='50%' cy='48%' r='68%'>"
        "<stop offset='55%' stop-color='#ffffff' stop-opacity='0'/>"
        f"<stop offset='100%' stop-color='{BG}' stop-opacity='0.85'/>"
        "</radialGradient>"
        # faint repeating scanline pattern
        "<pattern id='scan' width='3' height='3' patternUnits='userSpaceOnUse'>"
        f"<rect width='3' height='2' fill='{SCAN}' opacity='0'/>"
        f"<rect y='2' width='3' height='1' fill='{SCAN}' opacity='0.28'/>"
        "</pattern>"
        "</defs>"
    )


def _scan_layer() -> str:
    # static scanlines + a slow-rolling refresh bar (the CRT "restless" feel)
    roll = (
        f"<rect x='0' y='-12' width='{W}' height='14' fill='{PHOSPHOR}' opacity='0.045'>"
        f"<animate attributeName='y' values='-14;{H + 4}' dur='7.5s' "
        f"repeatCount='indefinite'/>"
        f"</rect>"
    )
    # whole-screen micro-flicker — phosphor never fully idle
    flicker = (
        f"<rect x='0' y='0' width='{W}' height='{H}' fill='{PHOSPHOR}' opacity='0'>"
        f"<animate attributeName='opacity' "
        f"values='0;0.03;0;0.015;0;0;0.025;0' "
        f"keyTimes='0;0.08;0.12;0.4;0.45;0.78;0.82;1' "
        f"dur='3.8s' repeatCount='indefinite'/>"
        f"</rect>"
    )
    return (
        f"<rect width='{W}' height='{H}' fill='url(#scan)' opacity='0.9'/>"
        f"{roll}{flicker}"
        f"<rect width='{W}' height='{H}' fill='url(#vignette)'/>"
    )


def _header() -> str:
    # ROBCO strip — short rule + service label, slightly dimmer than live text
    return (
        f"<text x='{INSET_X}' y='{HEADER_Y}' font-family='{FONT}' "
        f"font-size='12' font-weight='700' letter-spacing='1.4' "
        f"fill='{PHOSPHOR_DIM}' filter='url(#soft)'>{_escape(HEADER)}</text>"
        f"<line x1='{INSET_X}' y1='{RULE_Y}' x2='{W - INSET_X}' y2='{RULE_Y}' "
        f"stroke='{PHOSPHOR_FAINT}' stroke-width='1'/>"
        # small status pip, right side — "online"
        f"<text x='{W - INSET_X}' y='{HEADER_Y}' text-anchor='end' "
        f"font-family='{FONT}' font-size='11' font-weight='700' "
        f"fill='{PHOSPHOR_DIM}' letter-spacing='1.2'>ONLINE</text>"
    )


def _phrase_block(phrase: str, idx: int, n_phrases: int) -> tuple[str, str]:
    widths, segs, dur = _timeline(len(phrase))
    keytimes = _key_times(segs)

    def d_at(w: float) -> str:
        return f"M{TEXT_X:.1f},{LINE_Y} h{max(w, 0.01):.1f}"

    values = ";".join(d_at(w) for w in widths)
    cursor_xs = ";".join(f"{TEXT_X + w:.1f}" for w in widths)
    begin = (
        f"{START_DELAY}s;a{n_phrases - 1}.end" if idx == 0 else f"a{idx - 1}.end"
    )
    pid, aid = f"p{idx}", f"a{idx}"

    path = (
        f"<path id='{pid}' d='{d_at(0)}' fill='none'>"
        f"<animate id='{aid}' attributeName='d' begin='{begin}' "
        f"dur='{dur}ms' fill='freeze' calcMode='discrete' "
        f"values='{values}' keyTimes='{keytimes}'/>"
        f"</path>"
        f"<text font-family='{FONT}' fill='{PHOSPHOR}' font-size='{FONT_SIZE}' "
        f"font-weight='600' dominant-baseline='middle' filter='url(#glow)'>"
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

    prompt = (
        f"<text x='{INSET_X}' y='{LINE_Y}' font-family='{FONT}' "
        f"font-size='{FONT_SIZE}' font-weight='700' fill='{PHOSPHOR}' "
        f"dominant-baseline='middle' filter='url(#glow)'>"
        f"{_escape(PROMPT)}</text>"
    )

    # block caret — classic reverse-video slab, duty cycle biased ON
    # (P1 phosphor persistence leaves a ghost of the lit state)
    cursor = (
        f"<rect x='{TEXT_X:.1f}' y='{CURSOR_Y}' width='{CURSOR_W:.1f}' "
        f"height='{CURSOR_H}' fill='{AMBER_HINT}' filter='url(#glow)'>"
        f"{''.join(cursors)}"
        f"<animate attributeName='opacity' "
        f"values='1;1;0.15;0.15' keyTimes='0;0.55;0.6;1' "
        f"dur='1.05s' repeatCount='indefinite'/>"
        f"</rect>"
    )

    # outer bezel + inner glass
    shell = (
        f"<rect width='{W}' height='{H}' rx='4' ry='4' fill='{BG}' "
        f"stroke='{BORDER}' stroke-width='{BEZEL}'/>"
        f"<rect x='4' y='4' width='{W - 8}' height='{H - 8}' rx='2' ry='2' "
        f"fill='{FACE}'/>"
    )

    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' "
        f"xmlns:xlink='http://www.w3.org/1999/xlink' "
        f"width='{W}' height='{H}' viewBox='0 0 {W} {H}' role='img' "
        f"aria-label='Terminal: Tafseer Haque'>"
        f"{_filters()}"
        f"{shell}"
        f"<g>"
        f"{_scan_layer()}"
        f"{_header()}"
        f"{prompt}{''.join(paths)}{cursor}"
        f"</g>"
        f"</svg>"
    )


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "terminal_header.svg"
    svg = render_terminal_svg()
    open(out, "w").write(svg)

    for p in PHRASES:
        w, s, d = _timeline(len(p))
        assert len(s) == len(w) - 1 and d == sum(s)
        assert w[0] == 0.0 and w[-1] == 0.0 and max(w) == len(p) * CHAR_W
    assert "ROBCO" in svg and "url(#glow)" in svg and "url(#scan)" in svg
    assert "calcMode='discrete'" in svg and "fill='freeze'" in svg
    print(f"wrote {out} ({len(svg)} bytes)")
    print("ok")
