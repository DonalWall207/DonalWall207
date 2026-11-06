"""
Extra cards drawn from the same data as the main card:
GitHub stats card, top-languages card and a trophy row.
Each comes in a dark and light version, written to the cards/ folder.
Nothing here depends on an outside service, so they can't rate-limit or go down.
"""
import math
import os
from xml.sax.saxutils import escape

SANS = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

EXTRA = {  # per-theme colours the main card doesn't define
    "dark": dict(border="#30363d", tile="#0d1117", ring_bg="#30363d"),
    "light": dict(border="#d0d7de", tile="#ffffff", ring_bg="#d0d7de"),
}


def _svg(w, h, th, body):
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{SANS}">',
        "<style>@keyframes grow{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}"
        ".in{animation:grow .6s ease-out both}</style>",
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="12" fill="{th["bg"]}" stroke="{th["border"]}"/>',
        *body, "</svg>"])


# ───────────────────────────── stats card ─────────────────────────────
def grade(r):
    score = r["commits"] + 4 * r["stars"] + 2 * r["followers"] + 2 * r["repos"] + 3 * r["contrib"]
    steps = [(0, "C"), (50, "B"), (150, "A"), (400, "A+"), (1000, "S"), (2500, "S+")]
    for i in range(len(steps) - 1, -1, -1):
        if score >= steps[i][0]:
            lo = steps[i][0]
            hi = steps[i + 1][0] if i + 1 < len(steps) else lo * 2 or 1
            return steps[i][1], min(1.0, (score - lo) / (hi - lo))
    return "C", 0.0


ICONS = {  # 16x16 octicon-style outlines
    "star": "M8 .25l2.3 4.67 5.15.75-3.73 3.63.88 5.13L8 12.01 3.4 14.43l.88-5.13L.55 5.67l5.15-.75z",
    "commit": "M8 5a3 3 0 1 1 0 6 3 3 0 0 1 0-6zM0 7.25h4.6v1.5H0zm11.4 0H16v1.5h-4.6z",
    "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h9.75v13H4.5a1 1 0 0 0 0 2h9.75v1H4.5A2.5 2.5 0 0 1 2 13.5z",
    "people": "M5.5 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM0 14c0-3 2.5-4.5 5.5-4.5S11 11 11 14zm11-9a2 2 0 1 1 0 4 2 2 0 0 1 0-4zm1 5c2.2.3 4 1.6 4 4h-4z",
    "code": "M4.7 3.3 0 8l4.7 4.7 1.06-1.06L2.12 8l3.64-3.64zm6.6 0-1.06 1.06L13.88 8l-3.64 3.64 1.06 1.06L16 8z",
    "fork": "M5 3.25a1.75 1.75 0 1 1-3.5 0 1.75 1.75 0 0 1 3.5 0zM3.25 5v6m0 0a1.75 1.75 0 1 0 0 3.5 1.75 1.75 0 0 0 0-3.5zm9.5-9.5a1.75 1.75 0 1 1 0 3.5 1.75 1.75 0 0 1 0-3.5zm0 3.5c0 3-6.5 2.5-9.5 6",
}


def stats_card(th, s, title):
    r = s["_raw"]
    rows = [("star", "Total Stars Earned", s["stars"]),
            ("commit", "Total Commits", s["commits"]),
            ("repo", "Repositories", s["repos"]),
            ("fork", "Contributed to", s["contrib"]),
            ("people", "Followers", s["followers"]),
            ("code", "Lines of Code", s["loc"])]
    w, h = 485, 225
    body = [f'<text x="25" y="38" font-size="18" font-weight="600" fill="{th["key"]}">{escape(title)}</text>']
    for i, (ic, label, val) in enumerate(rows):
        y = 70 + i * 25
        body.append(f'<g class="in" style="animation-delay:{150 + i * 120}ms">'
                    f'<path transform="translate(25 {y - 12}) scale(.85)" d="{ICONS[ic]}" '
                    f'fill="{"none" if ic == "fork" else th["value"]}" stroke="{th["value"] if ic == "fork" else "none"}" stroke-width="1.5"/>'
                    f'<text x="50" y="{y}" font-size="14" fill="{th["text"]}">{label}:</text>'
                    f'<text x="240" y="{y}" font-size="14" font-weight="700" fill="{th["text"]}">{escape(val)}</text></g>')
    g, frac = grade(r) if r["commits"] or r["repos"] else ("—", 0)
    cx, cy, rad = 395, 120, 46
    circ = 2 * math.pi * rad
    body += [f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{th["ring_bg"]}" stroke-width="7"/>',
             f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{th["key"]}" stroke-width="7" '
             f'stroke-linecap="round" stroke-dasharray="{circ * frac:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>',
             f'<text x="{cx}" y="{cy + 9}" text-anchor="middle" font-size="26" font-weight="800" fill="{th["text"]}">{g}</text>']
    return _svg(w, h, th, body)


# ─────────────────────────── top languages card ──────────────────────────
def langs_card(th, s):
    langs = s["_langs"] or [("Run the workflow to load languages", th["dots"], 100.0)]
    w, h = 485, 225
    body = [f'<text x="25" y="38" font-size="18" font-weight="600" fill="{th["key"]}">Most Used Languages</text>',
            '<clipPath id="bar"><rect x="25" y="58" width="435" height="10" rx="5"/></clipPath>',
            '<g clip-path="url(#bar)">']
    x = 25.0
    for name, color, pct in langs:
        seg = 435 * pct / 100
        body.append(f'<rect x="{x:.2f}" y="58" width="{seg + .5:.2f}" height="10" fill="{color}"/>')
        x += seg
    body.append("</g>")
    for i, (name, color, pct) in enumerate(langs[:8]):
        col, row = i % 2, i // 2
        lx, ly = 25 + col * 220, 102 + row * 30
        label = escape(name) if len(langs) == 1 and not s["_langs"] else f"{escape(name)} {pct:.1f}%"
        body.append(f'<g class="in" style="animation-delay:{150 + i * 100}ms">'
                    f'<circle cx="{lx + 5}" cy="{ly - 5}" r="5" fill="{color}"/>'
                    f'<text x="{lx + 18}" y="{ly}" font-size="13" fill="{th["text"]}">{label}</text></g>')
    return _svg(w, h, th, body)


# ───────────────────────────── trophies ────────────────────────────────
RANKS = ["C", "B", "A", "S", "SS", "SSS"]
TROPHIES = [  # (title, stat key, thresholds for C..SSS, unit)
    ("Commits", "commits", [1, 100, 300, 700, 1500, 3000]),
    ("Repositories", "repos", [1, 5, 10, 20, 35, 60]),
    ("Stars", "stars", [1, 10, 30, 100, 300, 1000]),
    ("Followers", "followers", [1, 10, 25, 75, 200, 500]),
    ("Lines of Code", "loc", [1, 5_000, 20_000, 60_000, 150_000, 400_000]),
    ("Experience", "years", [1, 2, 3, 5, 7, 10]),
]
RANK_COL = {"SSS": "#e3b341", "SS": "#e3b341", "S": "#e3b341", "A": "#a5b4c4", "B": "#cd7f32", "C": "#8b949e"}


def _rank(v, steps):
    rank = None
    for i, t in enumerate(steps):
        if v >= t:
            rank = RANKS[i]
    return rank


def trophies_card(th, s):
    r = s["_raw"]
    tw, gap = 150, 13
    w, h = 985, 190
    x0 = (w - (6 * tw + 5 * gap)) / 2
    body = []
    for i, (title, key, steps) in enumerate(TROPHIES):
        v = r[key]
        rank = _rank(v, steps)
        col = RANK_COL.get(rank, th["dots"])
        x = x0 + i * (tw + gap)
        cx = x + tw / 2
        shown = f"{v:,} yrs" if key == "years" else f"{v:,}"
        if not r["commits"] and not r["repos"]:
            shown = "—"
        body.append(
            f'<g class="in" style="animation-delay:{100 + i * 110}ms">'
            f'<rect x="{x}" y="15" width="{tw}" height="160" rx="10" fill="{th["tile"]}" stroke="{th["border"]}"/>'
            # cup
            f'<path d="M{cx - 22} 35h44v18a22 22 0 0 1-44 0z" fill="{col}"/>'
            f'<path d="M{cx - 22} 41h-8a8 8 0 0 0 8 12M{cx + 22} 41h8a8 8 0 0 1-8 12" fill="none" stroke="{col}" stroke-width="3"/>'
            f'<rect x="{cx - 4}" y="74" width="8" height="10" fill="{col}"/>'
            f'<rect x="{cx - 15}" y="84" width="30" height="7" rx="2" fill="{col}"/>'
            f'<text x="{cx}" y="58" text-anchor="middle" font-size="{14 if rank and len(rank) > 2 else 17}" '
            f'font-weight="800" fill="{th["bg"]}">{rank or "?"}</text>'
            f'<text x="{cx}" y="122" text-anchor="middle" font-size="14" font-weight="600" fill="{th["key"]}">{title}</text>'
            f'<text x="{cx}" y="146" text-anchor="middle" font-size="13" fill="{th["text"]}">{shown}</text>'
            f'<text x="{cx}" y="164" text-anchor="middle" font-size="11" fill="{th["dots"]}">'
            f'{"Rank " + rank if rank else "Locked"}</text></g>')
    return _svg(w, h, th, body)


def write_all(themes, stats, title):
    os.makedirs("cards", exist_ok=True)
    for fname, base in themes.items():
        mode = "dark" if fname.startswith("dark") else "light"
        th = {**base, **EXTRA[mode]}
        for name, svg in (("stats", stats_card(th, stats, title)),
                          ("langs", langs_card(th, stats)),
                          ("trophies", trophies_card(th, stats))):
            path = f"cards/{name}_{mode}.svg"
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg)
            print("Wrote", path)
