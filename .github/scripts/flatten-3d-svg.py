#!/usr/bin/env python3
"""Reduce a github-profile-3d-contrib SVG to just its contribution calendar,
level the isometric projection so the year runs straight across, drop the
opaque background, and crop the canvas to what is left. The bars themselves are untouched -- only the angle the
grid is laid out at changes, so the 3D blocks still overlap front to back.

The generator lays out the SVG as <style>, a background <rect>, then four
top-level <g> elements: the calendar, the radar chart, the language pie and
the stats row. Everything after the first group is dropped.
"""

import math
import re
import sys
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)

# The generator lays the grid out on a 30 deg isometric axis, so a year runs
# down and to the right. Shearing the group by the same angle levels that axis
# without touching the bars drawn on it.
SHEAR = 30   # deg
PAD = 10     # px of breathing room around the calendar

FUNC = re.compile(r"(\w+)\(([^)]*)\)")
NUM = re.compile(r"-?[\d.]+(?:e-?\d+)?")


def matrix_of(transform):
    """Parse an SVG transform list into an (a, b, c, d, e, f) matrix."""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, raw in FUNC.findall(transform or ""):
        v = [float(n) for n in NUM.findall(raw)]
        if name == "translate":
            n = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            n = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "skewX":
            n = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY":
            n = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        elif name == "rotate":
            r = math.radians(v[0])
            n = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
        elif name == "matrix":
            n = tuple(v[:6])
        else:
            continue
        m = (
            m[0] * n[0] + m[2] * n[1],
            m[1] * n[0] + m[3] * n[1],
            m[0] * n[2] + m[2] * n[3],
            m[1] * n[2] + m[3] * n[3],
            m[0] * n[4] + m[2] * n[5] + m[4],
            m[1] * n[4] + m[3] * n[5] + m[5],
        )
    return m


def apply(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def bounds(node, parent=(1.0, 0.0, 0.0, 1.0, 0.0, 0.0), box=None):
    """Bounding box of every <rect> under `node`, in the outermost user space."""
    box = box or [float("inf"), float("inf"), float("-inf"), float("-inf")]
    m = matrix_of(node.get("transform"))
    m = (
        parent[0] * m[0] + parent[2] * m[1],
        parent[1] * m[0] + parent[3] * m[1],
        parent[0] * m[2] + parent[2] * m[3],
        parent[1] * m[2] + parent[3] * m[3],
        parent[0] * m[4] + parent[2] * m[5] + parent[4],
        parent[1] * m[4] + parent[3] * m[5] + parent[5],
    )
    if node.tag == f"{{{SVG}}}rect":
        x = float(node.get("x", 0))
        y = float(node.get("y", 0))
        w = float(node.get("width", 0))
        h = float(node.get("height", 0))
        for cx, cy in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
            px, py = apply(m, cx, cy)
            box[0] = min(box[0], px)
            box[1] = min(box[1], py)
            box[2] = max(box[2], px)
            box[3] = max(box[3], py)
    for child in node:
        bounds(child, m, box)
    return box


def flatten(path):
    tree = ET.parse(path)
    root = tree.getroot()

    groups = [c for c in root if c.tag == f"{{{SVG}}}g"]
    if not groups:
        sys.exit(f"{path}: no <g> element -- not a profile-3d-contrib SVG?")
    calendar, panels = groups[0], groups[1:]
    for g in panels:
        root.remove(g)

    calendar.set("transform", f"skewY(-{SHEAR})")

    x0, y0, x1, y1 = bounds(calendar)
    x0, y0, x1, y1 = x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD
    w, h = x1 - x0, y1 - y0

    root.set("width", f"{w:.0f}")
    root.set("height", f"{h:.0f}")
    root.set("viewBox", f"{x0:.2f} {y0:.2f} {w:.2f} {h:.2f}")

    for rect in root.findall(f"{{{SVG}}}rect"):
        root.remove(rect)   # the background fill; the page shows through instead

    tree.write(path, encoding="unicode", xml_declaration=False)
    print(f"{path}: dropped {len(panels)} panels, canvas now {w:.0f}x{h:.0f}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        flatten(arg)
