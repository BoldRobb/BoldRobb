"""Regenerates the profile SVGs in assets/ from GitHub data. Standard library only, so the workflow needs no installs."""

import base64
import json
import math
import os
import random
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
LOGIN = "BoldRobb"
STATION_TZ = timezone(timedelta(hours=-7))
CODING_SINCE = datetime(2021, 8, 1, tzinfo=STATION_TZ)

DEEP = "#0e1428"
GRID = "#2d4a8a"
GLOW = "#6fe3ff"
SIGNAL = "#fc3d21"
BONE = "#e6e9f2"
DIM = "#8a90a3"

THEMES = {
    "dark": {"text": BONE, "dim": DIM, "accent": GLOW, "star": GRID,
             "levels": ["#1b2c55", "#2d4a8a", "#3a6db0", "#4c9bd2", "#6fe3ff", "#c9f6ff"]},
    "light": {"text": DEEP, "dim": "#5b6478", "accent": "#1f63b8", "star": "#b9c6e0",
              "levels": ["#c9d4ea", "#a3b6dc", "#7393cb", "#4573bb", "#1f5aae", "#0d3a82"]},
}

STACK = [
    "openjdk", "python", "typescript", "javascript", "cplusplus", "csharp",
    "springboot", "fastapi", "django", "nodedotjs", "react", "nextdotjs",
    "angular", "flutter", "postgresql", "mysql", "prisma", "redis",
    "apachekafka", "docker", "kubernetes", "amazonwebservices", "githubactions", "git",
]


QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { name stargazerCount primaryLanguage { name } }
    }
  }
}
"""


def fetch_stats():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "User-Agent": LOGIN},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        payload = json.load(res)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    user = payload["data"]["user"]
    repos = [r for r in user["repositories"]["nodes"] if r["name"] != LOGIN]
    langs = {}
    for repo in repos:
        if repo["primaryLanguage"]:
            name = repo["primaryLanguage"]["name"]
            langs[name] = langs.get(name, 0) + 1
    return {
        "repos": len(repos),
        "stars": sum(r["stargazerCount"] for r in repos),
        "followers": user["followers"]["totalCount"],
        "contributions": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "langs": sorted(langs.items(), key=lambda kv: (-kv[1], kv[0])),
    }


def uptime(now):
    months = (now.year - CODING_SINCE.year) * 12 + now.month - CODING_SINCE.month
    years, months = divmod(months, 12)
    return f"{years} años, {months} {'mes' if months == 1 else 'meses'}"


def font_face(family, file, weight):
    data = base64.b64encode((ASSETS / "fonts" / file).read_bytes()).decode()
    return (f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');}}")


FONTS = None


def fonts():
    global FONTS
    if FONTS is None:
        FONTS = (font_face("Plex", "plexmono-400.woff2", 400)
                 + font_face("Plex", "plexmono-500.woff2", 500)
                 + font_face("ArchivoX", "archivo-x700.woff2", 700))
    return FONTS


# ── ASCII black hole ──────────────────────────────────────────────────

COLS, ROWS = 64, 22
CELL_W, CELL_H = 6.9, 14.0
FRAMES = 24
FRAME_S = 0.12
RAMP = " .·:-=+*"
TILT, SHADOW, DISK_IN, DISK_OUT, HALO = 0.3, 62.0, 84.0, 228.0, 1.18


def hole_frame(phase):
    """A tilted accretion disk around a shadow, with the far side of the disk lensed into a halo above it."""
    cx, cy = COLS * CELL_W / 2, ROWS * CELL_H / 2
    cells = {}
    for r in range(ROWS):
        for c in range(COLS):
            x, y = (c + 0.5) * CELL_W - cx, (r + 0.5) * CELL_H - cy
            rho_s = math.hypot(x, y)
            rho = math.hypot(x, y / TILT)
            theta = math.atan2(y / TILT, x)
            front, disk = y > 0, DISK_IN < rho < DISK_OUT
            val = 0.0
            if disk and (front or rho_s > SHADOW):
                arms = 0.5 + 0.5 * math.sin(2 * theta - phase + rho * 0.05)
                fall = (1 - (rho - DISK_IN) / (DISK_OUT - DISK_IN)) ** 0.6
                doppler = 0.78 + 0.22 * math.cos(theta + math.pi)
                val = min(1.0, 1.15 * fall * (0.5 + 0.5 * arms) * doppler)
            ring = rho_s - SHADOW * HALO
            if -6 < ring < 14 and not (front and disk):
                halo = (1 - abs(ring - 2) / 12) * (0.75 + 0.25 * math.cos(math.atan2(y, x) + phase))
                val = max(val, halo * (1.0 if y < 0 else 0.6))
            if rho_s < SHADOW and not (front and disk):
                continue
            if val < 0.1:
                continue
            ch = RAMP[min(len(RAMP) - 1, int(val * len(RAMP)))]
            if ch != " ":
                cells[(r, c)] = (ch, min(5, int(val * 6.2)))
    return cells


def frame_rows(cells, x0, y0):
    rows = []
    for r in range(ROWS):
        line = sorted((c, ch, lv) for (rr, c), (ch, lv) in cells.items() if rr == r)
        spans, i = [], 0
        while i < len(line):
            c0, text, lv = line[i]
            prev, i = c0, i + 1
            while i < len(line) and line[i][2] == lv:
                text += " " * (line[i][0] - prev - 1) + line[i][1]
                prev, i = line[i][0], i + 1
            spans.append(f'<tspan x="{x0 + c0 * CELL_W:.1f}" class="l{lv}">{escape(text)}</tspan>')
        if spans:
            rows.append(f'<text y="{y0 + r * CELL_H:.1f}" xml:space="preserve">{"".join(spans)}</text>')
    return "".join(rows)


def ascii_scene(x0, y0, theme):
    frames, used = [], set()
    for f in range(FRAMES):
        cells = hole_frame(2 * math.pi * f / FRAMES)
        used |= cells.keys()
        frames.append(f'<g class="fr" style="animation-delay:{f * FRAME_S:.2f}s">{frame_rows(cells, x0, y0)}</g>')
    rng = random.Random(9)
    stars = []
    for _ in range(110):
        r, c = rng.randrange(ROWS), rng.randrange(COLS)
        if (r, c) in used:
            continue
        twinkle = ' class="tw"' if rng.random() < 0.3 else ""
        stars.append(f'<text x="{x0 + c * CELL_W:.1f}" y="{y0 + r * CELL_H:.1f}"{twinkle} '
                     f'style="animation-delay:{rng.random() * 4:.2f}s">{rng.choice(".·")}</text>')
    css = "".join(f".l{i}{{fill:{c}}}" for i, c in enumerate(theme["levels"]))
    period = FRAMES * FRAME_S
    css += (f".fr{{opacity:0;animation:fr {period:.2f}s step-end infinite}}"
            f"@keyframes fr{{0%{{opacity:1}}{100 / FRAMES:.3f}%{{opacity:0}}100%{{opacity:0}}}}"
            f".tw{{animation:tw 4s ease-in-out infinite}}@keyframes tw{{0%,100%{{opacity:.25}}50%{{opacity:1}}}}")
    body = (f'<g class="mono" font-size="11.5" fill="{theme["star"]}">{"".join(stars)}</g>'
            f'<g class="mono" font-size="11.5">{"".join(frames)}</g>')
    return css, body


def card(stats, now, theme):
    w, h = 1000, 330
    css, scene = ascii_scene(0, 14, theme)
    total = sum(n for _, n in stats["langs"]) or 1
    langs = " · ".join(f"{name} {round(100 * n / total)}%" for name, n in stats["langs"][:4])
    rows = [
        ("Rol", "Full stack developer"),
        ("Órbita", "Neuronix · antes Macronnect"),
        ("Estudios", "Ing. de Software · UAS"),
        ("Estación", "Los Mochis, MX · UTC−7"),
        ("Idiomas", "ES nativo · EN B2"),
        ("Uptime", uptime(now)),
        None,
        ("Repos", f"{stats['repos']} públicos" + (f" · {stats['stars']} estrellas" if stats["stars"] else "")),
        ("Contribuciones", f"{stats['contributions']:,} en el último año"),
        ("Lenguajes", langs),
    ]
    x, y = 500, 42
    out = [f'<text x="{x}" y="{y}" class="disp" font-size="22" letter-spacing="1.5" fill="{theme["text"]}">ROBERTO BETANCOURT SOTO</text>',
           f'<text x="{x}" y="{y + 24}" class="mono" font-size="12.5" fill="{theme["dim"]}">Construyo software real, del frontend al despliegue.</text>']
    y += 58
    for row in rows:
        if row is None:
            y += 10
            continue
        k, v = row
        out.append(f'<text x="{x}" y="{y}" class="mono" font-size="12.5" xml:space="preserve">'
                   f'<tspan fill="{theme["accent"]}" font-weight="500">{escape(k)}</tspan>'
                   f'<tspan fill="{theme["dim"]}">: </tspan><tspan fill="{theme["text"]}">{escape(v)}</tspan></text>')
        y += 20
    y += 8
    for i, color in enumerate(theme["levels"]):
        out.append(f'<rect x="{x + i * 22}" y="{y}" width="18" height="10" fill="{color}"/>')
    out.append(f'<rect x="{x + 6 * 22}" y="{y}" width="18" height="10" fill="{SIGNAL}"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Roberto Betancourt Soto, full stack developer">
<style>{fonts()}.mono{{font-family:'Plex',ui-monospace,monospace}}.disp{{font-family:'ArchivoX','Arial Black',sans-serif;font-weight:700}}{css}</style>
{scene}
{''.join(out)}
</svg>"""


def icon_path(slug):
    raw = (ASSETS / "icons" / f"{slug}.svg").read_text(encoding="utf-8")
    return re.search(r' d="([^"]+)"', raw).group(1)


def stack(theme):
    per_row, size, gap = 12, 34, 44
    rows = math.ceil(len(STACK) / per_row)
    w = per_row * size + (per_row - 1) * gap
    h = rows * size + (rows - 1) * 26
    icons = []
    for i, slug in enumerate(STACK):
        r, c = divmod(i, per_row)
        icons.append(f'<svg x="{c * (size + gap)}" y="{r * (size + 26)}" width="{size}" height="{size}" viewBox="0 0 24 24">'
                     f'<path d="{icon_path(slug)}"/></svg>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Stack">
<g fill="{theme['text']}">{''.join(icons)}</g>
</svg>"""


def main():
    now = datetime.now(STATION_TZ)
    stats = fetch_stats()
    for name, theme in THEMES.items():
        (ASSETS / f"card-{name}.svg").write_text(card(stats, now, theme), encoding="utf-8")
        (ASSETS / f"stack-{name}.svg").write_text(stack(theme), encoding="utf-8")


if __name__ == "__main__":
    main()
