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

VOID = "#05070f"
DEEP = "#0e1428"
GRID = "#2d4a8a"
GLOW = "#6fe3ff"
SIGNAL = "#fc3d21"
BONE = "#e6e9f2"
DIM = "#8a90a3"

LEVELS = ["#1b2c55", "#2d4a8a", "#3a6db0", "#4c9bd2", "#6fe3ff", "#c9f6ff"]

STACK = [
    ("LENGUAJES", [("openjdk", "Java"), ("python", "Python"), ("typescript", "TypeScript"),
                   ("javascript", "JavaScript"), ("cplusplus", "C++"), ("csharp", "C#")]),
    ("BACKEND", [("springboot", "Spring Boot"), ("fastapi", "FastAPI"), ("django", "Django"),
                 ("nodedotjs", "Node.js")]),
    ("FRONTEND · MÓVIL", [("react", "React"), ("nextdotjs", "Next.js"), ("angular", "Angular"),
                          ("flutter", "Flutter")]),
    ("DATOS", [("postgresql", "PostgreSQL"), ("mysql", "MySQL"), ("prisma", "Prisma"),
               ("redis", "Redis"), ("apachekafka", "Kafka")]),
    ("DEVOPS · NUBE", [("docker", "Docker"), ("kubernetes", "Kubernetes"), ("amazonwebservices", "AWS"),
                       ("githubactions", "Actions"), ("git", "Git")]),
]

LINKS = [
    ("email", "EMAIL"),
    ("linkedin", "LINKEDIN"),
    ("x", "X / TWITTER"),
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


BASE_CSS = f"""
.mono{{font-family:'Plex',ui-monospace,monospace}}
.disp{{font-family:'ArchivoX','Arial Black',sans-serif;font-weight:700}}
.tag{{font-size:11px;letter-spacing:2.2px;fill:{GLOW}}}
.key{{font-size:11px;letter-spacing:1.6px;fill:{DIM}}}
.val{{font-size:12.5px;fill:{BONE};font-weight:500}}
.dim{{fill:{DIM}}}
"""


def backdrop(w, h, grid_step=40):
    lines = []
    for x in range(grid_step, w, grid_step):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}"/>')
    for y in range(grid_step, h, grid_step):
        lines.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}"/>')
    t = 14
    ticks = (f"M1 {t+1}V1H{t+1} M{w-t-1} 1H{w-1}V{t+1} M{w-1} {h-t-1}V{h-1}H{w-t-1} "
             f"M{t+1} {h-1}H1V{h-t-1}")
    return f"""
<defs>
  <radialGradient id="g1" cx="0" cy="0" r="0.9"><stop offset="0" stop-color="{GLOW}" stop-opacity=".10"/><stop offset="1" stop-color="{GLOW}" stop-opacity="0"/></radialGradient>
  <radialGradient id="g2" cx="1" cy="1" r="0.8"><stop offset="0" stop-color="{SIGNAL}" stop-opacity=".07"/><stop offset="1" stop-color="{SIGNAL}" stop-opacity="0"/></radialGradient>
  <radialGradient id="g3" cx=".5" cy=".15" r=".9"><stop offset="0" stop-color="{DEEP}"/><stop offset=".65" stop-color="{VOID}"/></radialGradient>
</defs>
<rect width="{w}" height="{h}" fill="url(#g3)"/>
<g stroke="{GRID}" stroke-opacity=".22" stroke-width="1">{''.join(lines)}</g>
<rect width="{w}" height="{h}" fill="url(#g1)"/>
<rect width="{w}" height="{h}" fill="url(#g2)"/>
<rect x=".5" y=".5" width="{w-1}" height="{h-1}" fill="none" stroke="{GRID}"/>
<path d="{ticks}" fill="none" stroke="{GLOW}" stroke-width="2"/>
"""


def plate(x, y, w, h, left, right=""):
    out = [f'<rect x="{x+.5}" y="{y+.5}" width="{w}" height="{h}" fill="{VOID}" fill-opacity=".55" stroke="{GRID}"/>']
    lw = len(left) * 6.6 + 16
    out.append(f'<rect x="{x+14}" y="{y-6}" width="{lw:.0f}" height="13" fill="{VOID}"/>')
    out.append(f'<text x="{x+22}" y="{y+4}" class="mono tag">{escape(left)}</text>')
    if right:
        rw = len(right) * 6.6 + 16
        out.append(f'<rect x="{x+w-14-rw:.0f}" y="{y-6}" width="{rw:.0f}" height="13" fill="{VOID}"/>')
        out.append(f'<text x="{x+w-22}" y="{y+4}" text-anchor="end" class="mono key">{escape(right)}</text>')
    return "\n".join(out)


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


def ascii_scene(x0, y0):
    frames, used, marks = [], set(), []
    for f in range(FRAMES):
        char, level, marks = render_frame(2 * math.pi * f / FRAMES)
        used |= {(r, c) for r in range(ROWS) for c in range(COLS) if char[r][c] != " "}
        frames.append(f'<g class="fr" style="animation-delay:{f * 0.28:.2f}s">{frame_rows(char, level, x0, y0)}</g>')
    rng = random.Random(7)
    stars = []
    for _ in range(70):
        r, c = rng.randrange(ROWS), rng.randrange(COLS)
        if (r, c) in used:
            continue
        twinkle = ' class="tw"' if rng.random() < 0.25 else ""
        stars.append(f'<text x="{x0 + c * CELL_W:.1f}" y="{y0 + r * CELL_H:.1f}"{twinkle} '
                     f'style="animation-delay:{rng.random() * 4:.2f}s">{rng.choice(".·")}</text>')
    legend_y = y0 + ROWS * CELL_H + 8
    entries = [("l6" if i == 0 else "l5", ("@" if i == 0 else "O" if m > 0.5 else "o") + " " + label + (" · LIVE" if i == 0 else ""))
               for i, (_, _, m, label) in enumerate(MASSES)]
    tag = (f'<text x="{x0}" y="{legend_y:.1f}" class="mono" font-size="9" letter-spacing=".8" xml:space="preserve">'
           + "  ".join(f'<tspan class="{cls}">{escape(t)}</tspan>' for cls, t in entries) + "</text>")
    css = "".join(f".l{i}{{fill:{c}}}" for i, c in enumerate(LEVELS)) + f".l6{{fill:{SIGNAL}}}"
    period = FRAMES * 0.28
    css += (f".fr{{opacity:0;animation:fr {period:.2f}s step-end infinite}}"
            f"@keyframes fr{{0%{{opacity:1}}{100 / FRAMES:.3f}%{{opacity:0}}100%{{opacity:0}}}}"
            f".tw{{animation:tw 4s ease-in-out infinite}}@keyframes tw{{0%,100%{{opacity:.25}}50%{{opacity:1}}}}")
    body = (f'<g class="mono" font-size="11.5" fill="{GRID}">{"".join(stars)}</g>'
            f'<g class="mono" font-size="11.5">{"".join(frames)}</g>{tag}')
    return css, body


# ── SVG builders ──────────────────────────────────────────────────────

def card(stats, now):
    w, h = 1000, 640
    css, scene = ascii_scene(46, 232)
    rows = [
        ("ROL", "Full stack developer"),
        ("ÓRBITA ACTUAL", "Neuronix"),
        ("ÓRBITA PREVIA", "Macronnect"),
        ("ESTUDIOS", "Ing. de Software · UAS"),
        ("IDIOMAS", "ES nativo · EN B2"),
        ("UPTIME", uptime(now)),
    ]
    tele = [
        ("REPOS PÚBLICOS", f"{stats['repos']:,}"),
        ("CONTRIBUCIONES · 12M", f"{stats['contributions']:,}"),
        ("ESTRELLAS", f"{stats['stars']:,}"),
        ("SEGUIDORES", f"{stats['followers']:,}"),
    ]
    rx, rw, y = 530, 438, 236
    right = []
    for k, v in rows:
        right.append(f'<text x="{rx + 20}" y="{y}" class="mono key">{escape(k)}</text>'
                     f'<text x="{rx + rw - 20}" y="{y}" text-anchor="end" class="mono val">{escape(v)}</text>')
        y += 25
    y += 6
    right.append(f'<line x1="{rx + 20}" y1="{y}" x2="{rx + rw - 20}" y2="{y}" stroke="{GRID}"/>'
                 f'<rect x="{rx + 32}" y="{y - 7}" width="150" height="14" fill="{VOID}"/>'
                 f'<text x="{rx + 40}" y="{y + 4}" class="mono tag">TELEMETRÍA · GITHUB</text>')
    y += 30
    for k, v in tele:
        right.append(f'<text x="{rx + 20}" y="{y}" class="mono key">{escape(k)}</text>'
                     f'<text x="{rx + rw - 20}" y="{y}" text-anchor="end" class="mono val">{escape(v)}</text>')
        y += 25
    total = sum(n for _, n in stats["langs"]) or 1
    top = stats["langs"][:5]
    other = total - sum(n for _, n in top)
    if other:
        top.append(("Otros", other))
    bx, bw = rx + 20, rw - 40
    right.append(f'<text x="{bx}" y="{y}" class="mono key">LENGUAJES · REPOS</text>')
    y += 12
    palette = [GLOW, "#3fa3d6", "#2f6fc0", GRID, DIM, "#4a5068"]
    x = bx
    legend = []
    for i, (name, n) in enumerate(top):
        seg = bw * n / total
        right.append(f'<rect x="{x:.1f}" y="{y}" width="{max(seg - 2, 1):.1f}" height="7" fill="{palette[i]}"/>')
        x += seg
        legend.append((palette[i], f"{name} {round(100 * n / total)}%"))
    y += 26
    lx = bx
    for color, label in legend:
        width = len(label) * 6.6 + 22
        if lx + width > bx + bw:
            lx, y = bx, y + 18
        right.append(f'<rect x="{lx}" y="{y - 7}" width="7" height="7" fill="{color}"/>'
                     f'<text x="{lx + 12}" y="{y}" class="mono" font-size="11" fill="{BONE}">{escape(label)}</text>')
        lx += width
    stamp = now.strftime("%Y-%m-%d")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Roberto Betancourt Soto, full stack developer">
<style>{fonts()}{BASE_CSS}{css}</style>
{backdrop(w, h)}
<text x="32" y="40" class="mono tag">PL-00 · BOLDROBB</text>
<text x="{w - 32}" y="40" text-anchor="end" class="mono key">LOS MOCHIS, MX · 25.79°N 108.99°W · UTC−7</text>
<text x="32" y="102" class="disp" font-size="40" letter-spacing="2" fill="{BONE}">ROBERTO BETANCOURT SOTO</text>
<text x="32" y="134" class="mono" font-size="13" letter-spacing="2.4" fill="{GLOW}">INGENIERO DE SOFTWARE · FULL STACK</text>
<text x="32" y="158" class="mono" font-size="13.5" fill="{DIM}">Construyo software real, del frontend al despliegue.</text>
{plate(32, 196, 470, 372, "PL-01 · POZO", f"MASAS {len(MASSES):02d}")}
{scene}
{plate(rx, 196, rw, 372, "PL-02 · SISTEMA", "EN LÍNEA")}
{''.join(right)}
<circle cx="38" cy="{h - 34}" r="4" fill="{SIGNAL}"><animate attributeName="opacity" values="1;.25;1" dur="2s" repeatCount="indefinite"/></circle>
<text x="50" y="{h - 30}" class="mono tag" fill="{BONE}" style="fill:{BONE}">ABIERTO A TRABAJO REMOTO</text>
<text x="{w - 32}" y="{h - 30}" text-anchor="end" class="mono key">ACTUALIZADO {stamp} · AUTO</text>
</svg>"""
    return svg


def icon_path(slug):
    raw = (ASSETS / "icons" / f"{slug}.svg").read_text(encoding="utf-8")
    return re.search(r' d="([^"]+)"', raw).group(1)


def stack():
    w = 1000
    row_h, top = 86, 64
    h = top + row_h * len(STACK) + 30
    count = sum(len(items) for _, items in STACK)
    out = []
    for i, (group, items) in enumerate(STACK):
        y = top + i * row_h
        if i:
            out.append(f'<line x1="32" y1="{y}" x2="{w - 32}" y2="{y}" stroke="{GRID}" stroke-opacity=".6"/>')
        out.append(f'<text x="32" y="{y + 46}" class="mono tag">{i + 1:02d}</text>'
                   f'<text x="64" y="{y + 46}" class="mono key" fill="{BONE}" style="fill:{BONE}">{escape(group)}</text>')
        for j, (slug, label) in enumerate(items):
            cx = 300 + j * 112
            out.append(f'<svg x="{cx - 15}" y="{y + 16}" width="30" height="30" viewBox="0 0 24 24" filter="url(#glow)">'
                       f'<path d="{icon_path(slug)}" fill="{BONE}"/></svg>'
                       f'<text x="{cx}" y="{y + 68}" text-anchor="middle" class="mono" font-size="10.5" letter-spacing=".6" fill="{DIM}">{escape(label)}</text>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Stack: {escape(', '.join(l for _, items in STACK for _, l in items))}">
<style>{fonts()}{BASE_CSS}</style>
<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur in="SourceAlpha" stdDeviation="1.6" result="b"/><feFlood flood-color="{GLOW}" flood-opacity=".55"/><feComposite in2="b" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
{backdrop(w, h)}
<text x="32" y="40" class="mono tag">PL-03 · STACK</text>
<text x="{w - 32}" y="40" text-anchor="end" class="mono key">{count} HERRAMIENTAS · {len(STACK)} ÓRBITAS</text>
{''.join(out)}
</svg>"""


def link_button(label):
    w, h = 190, 44
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>{fonts()}{BASE_CSS}</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" fill="{VOID}" stroke="{GRID}"/>
<path d="M1 9V1H9 M{w - 9} {h - 1}H{w - 1}V{h - 9}" fill="none" stroke="{GLOW}" stroke-width="2"/>
<text x="{w / 2}" y="27" text-anchor="middle" class="mono" font-size="12" font-weight="500" letter-spacing="2.4" fill="{BONE}">[ {escape(label)} ] →</text>
</svg>"""


def main():
    now = datetime.now(STATION_TZ)
    stats = fetch_stats()
    (ASSETS / "card.svg").write_text(card(stats, now), encoding="utf-8")
    (ASSETS / "stack.svg").write_text(stack(), encoding="utf-8")
    for slug, label in LINKS:
        (ASSETS / f"link-{slug}.svg").write_text(link_button(label), encoding="utf-8")


if __name__ == "__main__":
    main()
