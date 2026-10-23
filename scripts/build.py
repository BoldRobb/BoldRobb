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


# ── ASCII spacetime mesh ──────────────────────────────────────────────

COLS, ROWS = 64, 22
CELL_W, CELL_H = 6.9, 14.0
FRAMES = 12
MASSES = [  # (x, z, strength, label)
    (0.05, 0.0, 1.5, "NEURONIX"),
    (-0.62, -0.42, 0.55, "MACRONNECT"),
    (0.58, -0.55, 0.65, "CHANSHOP"),
    (-0.48, 0.55, 0.40, "TESIS"),
    (0.62, 0.48, 0.32, "FISIOVISION"),
    (-0.05, -0.85, 0.28, "DELFÍN"),
]


def height(x, z, phase):
    y = 0.0
    for mx, mz, m, _ in MASSES:
        d2 = (x - mx) ** 2 + (z - mz) ** 2
        y -= 0.55 * m / math.sqrt(1 + d2 / (0.035 * m))
    cx, cz = MASSES[0][0], MASSES[0][1]
    d = math.hypot(x - cx, z - cz)
    y += 0.04 * math.sin(14 * d - phase) * math.exp(-1.6 * d)
    return y


YAW, PITCH, DIST, FOCAL, V_ANCHOR = math.radians(0), math.radians(30), 2.0, 300.0, 0.32
EXTENT, LINES, RES, LINE_W = 1.8, 11, 360, 0.045
RAMP = "   ..·:;="


def project(x, y, z):
    cy, sy = math.cos(YAW), math.sin(YAW)
    x, z = x * cy - z * sy, x * sy + z * cy
    cp, sp = math.cos(PITCH), math.sin(PITCH)
    y, z = y * cp + z * sp, -y * sp + z * cp
    z += DIST
    px = COLS * CELL_W / 2 + FOCAL * x / z
    py = ROWS * CELL_H * V_ANCHOR - FOCAL * y / z
    return px, py, z


def direction_char(dx, dy):
    a = abs(math.degrees(math.atan2(dy, dx)))
    if a > 90:
        a = 180 - a
        dx = -dx
        dy = -dy
    if a < 24:
        return "-"
    if a > 66:
        return "|"
    return "\\" if (dx > 0) == (dy > 0) else "/"


def render_frame(phase):
    """Samples the height field densely, keeps the nearest sample per cell, and draws grid lines
    as direction glyphs over a sparse slope-shaded surface, the way VShelf's ascii-engine ramps materials."""
    step = 2 * EXTENT / (LINES - 1)
    h = 2 * EXTENT / RES
    coord = [-EXTENT + i * h for i in range(RES + 1)]
    hf = [[height(x, z, phase) for z in coord] for x in coord]
    zmin = [[math.inf] * COLS for _ in range(ROWS)]
    samples = []
    for i, x in enumerate(coord):
        for j, z in enumerate(coord):
            px, py, depth = project(x, hf[i][j], z)
            col, row = int(px / CELL_W), int(py / CELL_H)
            if 0 <= col < COLS and 0 <= row < ROWS:
                samples.append((row, col, depth, i, j))
                zmin[row][col] = min(zmin[row][col], depth)
    on_u = [[False] * COLS for _ in range(ROWS)]
    on_v = [[False] * COLS for _ in range(ROWS)]
    best = [[None] * COLS for _ in range(ROWS)]
    for row, col, depth, i, j in samples:
        if depth > zmin[row][col] + 0.06:
            continue
        gu, gv = (i * h) / step, (j * h) / step
        on_u[row][col] |= abs(gu - round(gu)) < LINE_W
        on_v[row][col] |= abs(gv - round(gv)) < LINE_W
        if depth == zmin[row][col]:
            best[row][col] = (i, j, depth)
    char = [[" "] * COLS for _ in range(ROWS)]
    level = [[0] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            if not best[r][c]:
                continue
            i, j, depth = best[r][c]
            i2, j2 = min(i + 1, RES), min(j + 1, RES)
            y = hf[i][j]
            p0 = project(coord[i], y, coord[j])
            heat = min(1.0, max(0.0, (-y - 0.2) / 0.6))
            near = max(0.0, min(1.0, (DIST + 1.2 - depth) / 2.4))
            if on_u[r][c] and on_v[r][c]:
                ch = "+"
            elif on_u[r][c]:
                p1 = project(coord[i], hf[i][j2], coord[j2])
                ch = direction_char(p1[0] - p0[0], p1[1] - p0[1])
            elif on_v[r][c]:
                p1 = project(coord[i2], hf[i2][j], coord[j])
                ch = direction_char(p1[0] - p0[0], p1[1] - p0[1])
            else:
                ch = RAMP[min(len(RAMP) - 1, int(heat * len(RAMP)))]
                level[r][c] = min(3, int((0.4 * near + 0.6 * heat) * 4))
                char[r][c] = ch
                continue
            char[r][c] = ch
            level[r][c] = min(5, int((0.5 * near + 0.8 * heat) * 5.5))
    marks = []
    for i, (mx, mz, m, label) in enumerate(MASSES):
        px, py, _ = project(mx, height(mx, mz, phase), mz)
        col, row = int(px / CELL_W), int(py / CELL_H)
        if 0 <= col < COLS and 0 <= row < ROWS:
            char[row][col] = "@" if i == 0 else ("O" if m > 0.5 else "o")
            level[row][col] = 6 if i == 0 else 5
            marks.append((col, row, label))
    return char, level, marks


def frame_rows(char, level, x0, y0):
    rows = []
    for r in range(ROWS):
        runs, cur, buf = [], None, []
        for c in range(COLS):
            ch, lv = char[r][c], level[r][c]
            if ch == " ":
                buf.append(" ")
                continue
            if cur is not None and lv != cur:
                runs.append((cur, "".join(buf)))
                buf = []
            cur = lv
            buf.append(ch)
        text = "".join(buf).rstrip()
        if cur is not None and text:
            runs.append((cur, text))
        if not runs:
            continue
        spans = "".join(f'<tspan class="l{lv}">{escape(t)}</tspan>' for lv, t in runs)
        rows.append(f'<text x="{x0}" y="{y0 + r * CELL_H:.1f}" xml:space="preserve">{spans}</text>')
    return "".join(rows)


def ascii_scene(x0, y0, theme):
    frames, used = [], set()
    for f in range(FRAMES):
        char, level, _ = render_frame(2 * math.pi * f / FRAMES)
        used |= {(r, c) for r in range(ROWS) for c in range(COLS) if char[r][c] != " "}
        frames.append(f'<g class="fr" style="animation-delay:{f * 0.28:.2f}s">{frame_rows(char, level, x0, y0)}</g>')
    rng = random.Random(7)
    stars = []
    for _ in range(50):
        r, c = rng.randrange(ROWS), rng.randrange(COLS)
        if (r, c) in used:
            continue
        twinkle = ' class="tw"' if rng.random() < 0.25 else ""
        stars.append(f'<text x="{x0 + c * CELL_W:.1f}" y="{y0 + r * CELL_H:.1f}"{twinkle} '
                     f'style="animation-delay:{rng.random() * 4:.2f}s">{rng.choice(".·")}</text>')
    css = "".join(f".l{i}{{fill:{c}}}" for i, c in enumerate(theme["levels"])) + f".l6{{fill:{SIGNAL}}}"
    period = FRAMES * 0.28
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
