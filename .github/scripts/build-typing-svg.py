#!/usr/bin/env python3
"""Render the profile code box as an SVG that types itself out on every load.

GitHub strips <script> from README HTML but plays CSS animation inside an SVG
that is referenced as an image, so the reveal is done with one clip path per
line whose width steps open a character at a time.
"""

import html
import re
import sys

FONT_SIZE = 13.5
CHAR_W = FONT_SIZE * 0.6        # monospace advance width
LINE_H = FONT_SIZE * 1.45
PAD_X, PAD_Y = 22, 20
RADIUS = 10

TOTAL_SECONDS = 3.0             # how long the whole box takes to type
CASCADE_SHARE = 0.45            # of that, the share spent staggering line starts

BG = "#0d1117"
PLAIN = "#c9d1d9"
COMMENT = "#5b6675"             # the ascii art column
KEYWORD = "#ff7b72"
NAME = "#ffa657"
STRING = "#a5d6ff"
CURSOR = "#ffa657"

KEYWORDS = {"class", "def", "return", "import", "from", "None", "True", "False"}

STRING_RE = re.compile(r'("""[^"]*"""|"[^"]*"|\'[^\']*\')')
NAME_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z_0-9]*)(\s*)(=|\s*=)")


def spans(code):
    """Split one line of code into (text, color) runs."""
    out = []
    m = NAME_RE.match(code)
    if m:
        out.append((m.group(1) + m.group(2), NAME))
        code = code[len(m.group(1)) + len(m.group(2)):]
    for part in STRING_RE.split(code):
        if not part:
            continue
        if STRING_RE.fullmatch(part):
            out.append((part, STRING))
        else:
            for word in re.split(r"(\b\w+\b)", part):
                if not word:
                    continue
                out.append((word, KEYWORD if word in KEYWORDS else PLAIN))
    return out


def line_runs(line):
    """Colour one full line, treating the trailing `#` column as a comment."""
    cut = line.find("  #")
    if cut == -1:
        return spans(line)
    return spans(line[:cut]) + [(line[cut:], COMMENT)]


def build(lines):
    # every line reveals at once; each one starts a beat after the line above
    step = TOTAL_SECONDS * CASCADE_SHARE / max(len(lines) - 1, 1)
    line_dur = TOTAL_SECONDS - step * (len(lines) - 1)

    cols = max(len(l) for l in lines)
    width = cols * CHAR_W + PAD_X * 2
    height = len(lines) * LINE_H + PAD_Y * 2

    css, body = [], []
    for i, line in enumerate(lines):
        start = i * step
        dur = line_dur
        w = len(line) * CHAR_W
        css.append(
            f"@keyframes t{i}{{from{{width:0}}to{{width:{w:.1f}px}}}}"
            f"#c{i} rect{{width:0;height:{LINE_H:.1f}px;"
            f"animation:t{i} {dur:.2f}s steps({max(len(line),1)}) {start:.2f}s forwards}}"
        )

        y = PAD_Y + i * LINE_H + FONT_SIZE
        runs, x = [], PAD_X
        for text, color in line_runs(line):
            if text.strip():
                runs.append(
                    f'<tspan x="{x:.1f}" y="{y:.1f}" fill="{color}" '
                    f'textLength="{len(text) * CHAR_W:.1f}" '
                    f'lengthAdjust="spacing">{html.escape(text)}</tspan>'
                )
            x += len(text) * CHAR_W

        body.append(
            f'<clipPath id="c{i}"><rect x="{PAD_X}" '
            f'y="{PAD_Y + i * LINE_H:.1f}"/></clipPath>'
            f'<text clip-path="url(#c{i})" xml:space="preserve">'
            + "".join(runs)
            + "</text>"
        )

    start = TOTAL_SECONDS
    cursor_y = PAD_Y + (len(lines) - 1) * LINE_H + 3
    css.append(
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        f"#cursor{{opacity:0;animation:blink 1s steps(1) {start:.2f}s infinite}}"
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" '
        f'font-size="{FONT_SIZE}">'
        f"<style>{''.join(css)}</style>"
        f'<rect width="100%" height="100%" rx="{RADIUS}" fill="{BG}"/>'
        + "".join(body)
        + f'<rect id="cursor" x="{PAD_X}" y="{cursor_y:.1f}" '
        f'width="{CHAR_W:.1f}" height="{FONT_SIZE:.1f}" fill="{CURSOR}"/>'
        "</svg>"
    )


if __name__ == "__main__":
    src = open(sys.argv[1]).read().split("\n")
    fence = [i for i, l in enumerate(src) if l.startswith("```")]
    lines = src[fence[0] + 1:fence[1]] if len(fence) >= 2 else src
    while lines and not lines[-1].strip():
        lines.pop()
    svg = build(lines)
    open(sys.argv[2], "w").write(svg)
    print(f"{sys.argv[2]}: {len(lines)} lines, {len(svg)} bytes")
