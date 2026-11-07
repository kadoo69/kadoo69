"""Generate the animated terminal profile card (dark + light SVG) from live GitHub data.

Standard library only. Reads GITHUB_TOKEN from the environment, or falls back to `gh auth token`.
Usage: python3 scripts/generate.py [login]
"""
import datetime as dt
import hashlib
import html
import json
import math
import os
import re
import subprocess
import sys
import urllib.request

LOGIN = sys.argv[1] if len(sys.argv) > 1 else "kadoo69"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

FIELDS = [
    ("domains", "finance / technology / mathematics"),
    ("languages", "python, c++, typescript"),
    ("interests", "markets, microstructure, applied math, ml"),
    ("stack", "pytorch, numpy, pandas, next.js"),
    ("writing", "the other side of the pull request"),
]

PALETTES = {
    "dark": dict(bg="#0b0d10", border="#21262d", text="#e6edf3", dim="#7d8590", accent="#3fb950", glow="#7ee787", blur=1.6,
                 chrome="#30363d", off="#161b22", heat=["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]),
    "light": dict(bg="#fbfbfb", border="#d8dee4", text="#1f2328", dim="#6e7781", accent="#1a7f37", glow="#2da44e", blur=0.6,
                  chrome="#d0d7de", off="#eaeef2", heat=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]),
}

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
CW = 8.4  # monospace advance at 14px, used only for sizing typed clips


def _raw_loss(x, y):
    bowl = 0.42 * (x * x + y * y)
    well = 0.80 * math.exp(-((x - 0.32) ** 2 + (y + 0.22) ** 2) / 0.10)
    trap = 0.38 * math.exp(-((x + 0.48) ** 2 + (y - 0.42) ** 2) / 0.06)
    texture = 0.05 * math.sin(4.2 * x) * math.cos(3.6 * y)
    return bowl - well - trap + texture


_GRID = [_raw_loss(-1 + i / 30, -1 + j / 30) for i in range(61) for j in range(61)]
_LO, _HI = min(_GRID), max(_GRID)


def loss(x, y):
    """Toy loss landscape on [-1, 1]^2, scaled to height [-0.42, 0.48]: a deep global basin and a shallow trap."""
    return (_raw_loss(x, y) - _LO) / (_HI - _LO) * 0.9 - 0.42


def descent(x, y, lr=0.012, beta=0.9, steps=110):
    """Heavy-ball gradient descent on loss(). Deterministic; returns the list of (x, y) iterates."""
    vx = vy = 0.0
    path = [(x, y)]
    for _ in range(steps):
        h = 1e-4
        gx = (loss(x + h, y) - loss(x - h, y)) / (2 * h)
        gy = (loss(x, y + h) - loss(x, y - h)) / (2 * h)
        vx, vy = beta * vx - lr * gx, beta * vy - lr * gy
        x, y = max(-1.0, min(1.0, x + vx)), max(-1.0, min(1.0, y + vy))
        path.append((x, y))
    return path


# Same start, two optimizers: momentum escapes the trap and finds the global minimum, plain GD gets stuck.
RUNS = [("momentum", (-0.9, 0.85), 0.012, 0.94), ("sgd", (-0.9, 0.85), 0.012, 0.0)]
DESCENT = (0.04, 0.62)  # loop fractions where the balls roll
FADE = "0;1;1;0;0", "0;0.04;0.9;0.98;1"  # values, keyTimes for trail and ball opacity


def scene_anim(box, n=48, k=100, lines=13, samples=20, trail_pts=40, tilt=0.62, dist=3.6, floor=-0.5):
    """Keyframes for one full turn of the loss landscape with two descending balls, fitted into box.

    Mesh keyframes are sampled n times per turn, balls and trails k times. Every keyframe keeps the
    same path structure, so SMIL interpolates smoothly between them.
    """
    cb, sb = math.cos(tilt), math.sin(tilt)
    grid = [-1 + 2 * i / (lines - 1) for i in range(lines)]
    ts = [-1 + 2 * i / (samples - 1) for i in range(samples)]

    def project(x, y, z, u):
        a = 2 * math.pi * u + 0.5
        ca, sa = math.cos(a), math.sin(a)
        x1, y1 = x * ca - y * sa, x * sa + y * ca
        d, zz = y1 * cb - z * sb, y1 * sb + z * cb
        s = 1.0 / (d + dist)
        return (s * x1, -s * zz), d

    raw_mesh, raw_floor, raw_lab = [], [], {"θ₁": [], "θ₂": []}
    for f in range(n):
        u = f / n
        polys = []
        for g in grid:
            for along_x in (True, False):
                pts, depth = [], 0.0
                for t in ts:
                    x, y = (t, g) if along_x else (g, t)
                    p, d = project(x, y, loss(x, y), u)
                    pts.append(p)
                    depth += d
                polys.append((pts, depth / len(ts)))
        raw_mesh.append(polys)
        raw_floor.append([project(x, y, floor, u)[0] for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))])
        raw_lab["θ₁"].append(project(0, -1.45, floor, u)[0])
        raw_lab["θ₂"].append(project(1.45, 0, floor, u)[0])

    paths = [descent(*start, lr=lr, beta=beta, steps=130) for _, start, lr, beta in RUNS]

    def at(path, q):
        i = min(int(q), len(path) - 2)
        w = q - i
        x = path[i][0] + w * (path[i + 1][0] - path[i][0])
        y = path[i][1] + w * (path[i + 1][1] - path[i][1])
        return x, y

    raw_trails = []
    for path in paths:
        trail_keys, ball_keys, shadow_keys = [], [], []
        for j in range(k):
            u = j / k
            prog = min(1.0, max(0.0, (u - DESCENT[0]) / (DESCENT[1] - DESCENT[0])))
            q = prog * (len(path) - 1)
            pts = []
            for m in range(trail_pts):
                x, y = at(path, q * m / (trail_pts - 1))
                pts.append(project(x, y, loss(x, y) + 0.012, u)[0])
            trail_keys.append(pts)
            x, y = at(path, q)
            ball_keys.append(project(x, y, loss(x, y) + 0.02, u)[0])
            shadow_keys.append(project(x, y, floor, u)[0])
        raw_trails.append((trail_keys, ball_keys, shadow_keys))

    allp = [p for fr in raw_mesh for pts, _ in fr for p in pts] + [p for fl in raw_floor for p in fl]
    xs, ys = [p[0] for p in allp], [p[1] for p in allp]
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / (max(xs) - min(xs)), (y1 - y0) / (max(ys) - min(ys)))
    ox = x0 + ((x1 - x0) - s * (max(xs) - min(xs))) / 2 - s * min(xs)
    oy = y0 + ((y1 - y0) - s * (max(ys) - min(ys))) / 2 - s * min(ys)

    def xy(p, nd=0):
        return round(ox + s * p[0], nd), round(oy + s * p[1], nd)

    def fmt(p, nd=0):
        a, b = xy(p, nd)
        return f"{a:g},{b:g}"

    def loop(keys):
        return keys + keys[:1]

    mesh = []
    for li in range(len(raw_mesh[0])):
        d_keys = ["M" + " ".join(fmt(p) for p in raw_mesh[f][li][0]) for f in range(n)]
        op_keys = [f"{0.22 + 0.78 * min(1.0, max(0.0, (1.2 - raw_mesh[f][li][1]) / 2.4)):.2f}" for f in range(n)]
        mesh.append((loop(d_keys), loop(op_keys)))
    trails = []
    for trail_keys, ball_keys, shadow_keys in raw_trails:
        trails.append({
            "d": loop(["M" + " ".join(fmt(p) for p in pts) for pts in trail_keys]),
            "ball": loop([xy(p, 1) for p in ball_keys]),
            "shadow": loop([xy(p, 1) for p in shadow_keys]),
        })
    return {
        "mesh": mesh,
        "floor": loop(["M" + " ".join(fmt(p) for p in fl) for fl in raw_floor]),
        "labels": {name: loop([xy(p) for p in v]) for name, v in raw_lab.items()},
        "trails": trails,
        "box": box,
    }


def token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def fetch():
    q = ('query($l:String!){user(login:$l){createdAt contributionsCollection{contributionCalendar'
         '{totalContributions weeks{contributionDays{date contributionLevel}}}}}}')
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"l": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token()}", "User-Agent": "profile-card"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        u = json.load(r)["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    return u["createdAt"][:4], cal["totalContributions"], cal["weeks"]


def esc(s):
    return html.escape(s, quote=False)


def typed(x, y, s, delay, cls="", size=14):
    dur = max(0.25, len(s) * 0.045)
    return (f'<text x="{x}" y="{y}" class="{cls}" style="font-size:{size}px;clip-path:inset(0 100% 0 0);'
            f'animation:t {dur:.2f}s steps({len(s)},end) {delay:.2f}s forwards">{esc(s)}</text>'), delay + dur


def render(theme, since, total, weeks):
    p = PALETTES[theme]
    out, W, H = [], 880, 584
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
               f'aria-label="Terminal card for Aarav Mahajan: finance, technology, mathematics. '
               f'{total} contributions in the last year.">')
    out.append(f'''<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;fill:{p["text"]}}}
.d{{fill:{p["dim"]}}} .a{{fill:{p["accent"]}}} .b{{font-weight:700}}
.r{{opacity:0;animation:r .01s forwards}}
@keyframes r{{to{{opacity:1}}}}
@keyframes t{{to{{clip-path:inset(0 0 0 0)}}}}
.cur{{fill:{p["text"]};animation:k 1.1s steps(1) infinite}}
@keyframes k{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;clip-path:none!important}}}}
</style>''')
    out.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="{p["bg"]}" stroke="{p["border"]}"/>')
    for i in range(3):
        out.append(f'<circle cx="{24+i*20}" cy="20" r="6" fill="{p["chrome"]}"/>')
    out.append(f'<text x="{W/2}" y="24" text-anchor="middle" class="d" style="font-size:12px">{LOGIN} : zsh</text>')
    out.append(f'<line x1="0" y1="40" x2="{W}" y2="40" stroke="{p["border"]}"/>')

    # prompt 1
    out.append('<text x="36" y="76" class="a b" style="font-size:14px">$</text>')
    s, t = typed(56, 76, "neofetch", 0.3)
    out.append(s)

    ix, y0, d0 = 300, 112, 1.1
    # loss landscape with two balls running gradient descent, in the neofetch logo slot
    sc = scene_anim((30, 86, 268, 300))
    anim = 'dur="20s" repeatCount="indefinite" calcMode="linear"'
    fade = f'<animate attributeName="opacity" values="{FADE[0]}" keyTimes="{FADE[1]}" {anim}/>'
    bx0, by0, bx1, by1 = sc["box"]

    def move(keys, ax, ay, dy=0):
        return (f'<animate attributeName="{ax}" values="{";".join(f"{k[0]:g}" for k in keys)}" {anim}/>'
                f'<animate attributeName="{ay}" values="{";".join(f"{k[1] + dy:g}" for k in keys)}" {anim}/>')

    out.append(f"""<defs>
<linearGradient id="hg" gradientUnits="userSpaceOnUse" x1="0" y1="{by0}" x2="0" y2="{by1}">
<stop offset="0" stop-color="{p["accent"]}" stop-opacity="0.95"/><stop offset="1" stop-color="{p["accent"]}" stop-opacity="0.35"/>
</linearGradient>
<filter id="gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{p["blur"]}" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<radialGradient id="halo"><stop offset="0" stop-color="{p["glow"]}" stop-opacity="0.55"/><stop offset="1" stop-color="{p["glow"]}" stop-opacity="0"/></radialGradient>
</defs>""")
    out.append('<g class="r" style="animation-delay:1.0s">')
    fl = sc["floor"]
    out.append(f'<path d="{fl[0]}" fill="none" stroke="{p["dim"]}" stroke-opacity="0.45" stroke-dasharray="2 4">'
               f'<animate attributeName="d" values="{";".join(fl)}" {anim}/></path>')
    for name, keys in sc["labels"].items():
        out.append(f'<text class="d" style="font-size:11px" text-anchor="middle" x="{keys[0][0]:g}" y="{keys[0][1] + 4:g}">{esc(name)}'
                   f'{move(keys, "x", "y", 4)}</text>')
    for tr in sc["trails"]:
        sh = tr["shadow"]
        out.append(f'<ellipse rx="4" ry="1.6" fill="{p["dim"]}" fill-opacity="0.5" opacity="0" cx="{sh[0][0]:g}" cy="{sh[0][1]:g}">{move(sh, "cx", "cy")}{fade}</ellipse>')
    out.append('<g fill="none" stroke="url(#hg)" stroke-width="1" stroke-linejoin="round">')
    for d_keys, op_keys in sc["mesh"]:
        out.append(f'<path d="{d_keys[0]}" stroke-opacity="{op_keys[0]}"><animate attributeName="d" values="{";".join(d_keys)}" {anim}/>'
                   f'<animate attributeName="stroke-opacity" values="{";".join(op_keys)}" {anim}/></path>')
    out.append('</g>')
    for i, tr in enumerate(sc["trails"]):
        color = p["glow"] if i == 0 else p["text"]
        out.append(f'<path d="{tr["d"][0]}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
                   f'opacity="0" filter="url(#gl)"><animate attributeName="d" values="{";".join(tr["d"])}" {anim}/>{fade}</path>')
        b = tr["ball"]
        out.append(f'<g opacity="0">{fade}'
                   f'<circle r="9" fill="url(#halo)" cx="{b[0][0]:g}" cy="{b[0][1]:g}">{move(b, "cx", "cy")}</circle>'
                   f'<circle r="3.4" fill="{color}" filter="url(#gl)" cx="{b[0][0]:g}" cy="{b[0][1]:g}">{move(b, "cx", "cy")}</circle></g>')
    out.append('</g>')
    cap_y = y0 + 44 + 6 * 26
    out.append(f'<g class="r" style="animation-delay:1.0s;font-size:11px">'
               f'<text class="d" x="36" y="{cap_y}">L(θ₁, θ₂)</text>'
               f'<circle cx="112" cy="{cap_y - 4}" r="3" fill="{p["glow"]}"/><text class="d" x="120" y="{cap_y}">{RUNS[0][0]}</text>'
               f'<circle cx="190" cy="{cap_y - 4}" r="3" fill="{p["text"]}"/><text class="d" x="198" y="{cap_y}">{RUNS[1][0]}</text></g>')

    # info panel
    head = f"aarav@{LOGIN}"
    out.append(f'<text class="r a b" style="font-size:14px;animation-delay:{d0:.2f}s" x="{ix}" y="{y0}">{esc(head)}</text>')
    out.append(f'<text class="r d" style="font-size:14px;animation-delay:{d0+0.1:.2f}s" x="{ix}" y="{y0+18}">{"-"*len(head)}</text>')
    rows = FIELDS + [("since", since), ("activity", f"{total} contributions / 12 months")]
    for i, (k, v) in enumerate(rows):
        y = y0 + 44 + i * 26
        d = d0 + 0.25 + i * 0.18
        out.append(f'<text class="r" style="font-size:14px;animation-delay:{d:.2f}s" y="{y}">'
                   f'<tspan x="{ix}" class="a">{esc(k)}</tspan><tspan x="{ix+11*CW:.1f}">{esc(v)}</tspan></text>')

    # prompt 2
    py = 352
    out.append(f'<text class="r a b" style="font-size:14px;animation-delay:3.1s" x="36" y="{py}">$</text>')
    s, t = typed(56, py, "./activity --last-12-months", 3.2)
    out.append(s)

    # heatmap
    hx, hy, hp, hc = 36, 394, 15, 11
    last_month = None
    for wi, wk in enumerate(weeks):
        days = wk["contributionDays"]
        if not days:
            continue
        m = int(days[0]["date"][5:7])
        if m != last_month and wi < len(weeks) - 2:
            name = dt.date(2000, m, 1).strftime("%b").lower()
            out.append(f'<text class="r d" style="font-size:10px;animation-delay:{4.2:.2f}s" x="{hx+wi*hp}" y="{hy-10}">{name}</text>')
            last_month = m
        d = 4.2 + wi * 0.025
        for di, day in enumerate(days):
            lv = LEVELS[day["contributionLevel"]]
            out.append(f'<rect class="r" style="animation-delay:{d:.2f}s" x="{hx+wi*hp}" y="{hy+di*hp}" width="{hc}" height="{hc}" rx="2.5" fill="{p["heat"][lv]}"/>')

    # legend
    ly = hy + 7 * hp + 22
    lx = hx + 53 * hp - 5 * 16 - 62
    out.append(f'<text class="r d" style="font-size:11px;animation-delay:5.6s" x="{lx}" y="{ly}">less</text>')
    for i in range(5):
        out.append(f'<rect class="r" style="animation-delay:5.6s" x="{lx+34+i*16}" y="{ly-10}" width="{hc}" height="{hc}" rx="2.5" fill="{p["heat"][i]}"/>')
    out.append(f'<text class="r d" style="font-size:11px;animation-delay:5.6s" x="{lx+34+5*16+4}" y="{ly}">more</text>')

    # final prompt
    fy = ly + 40
    out.append(f'<text class="r a b" style="font-size:14px;animation-delay:5.7s" x="36" y="{fy}">$</text>')
    out.append(f'<rect class="r cur" style="animation:r .01s 5.7s forwards,k 1.1s steps(1) 5.7s infinite" x="56" y="{fy-12}" width="8" height="16"/>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    since, total, weeks = fetch()
    os.makedirs(OUT, exist_ok=True)
    digest = hashlib.sha256()
    for theme in PALETTES:
        svg = render(theme, since, total, weeks) + "\n"
        digest.update(svg.encode())
        path = os.path.join(OUT, f"card-{theme}.svg")
        with open(path, "w") as f:
            f.write(svg)
        print("wrote", os.path.normpath(path))
    # GitHub's image CDN caches by URL, so version the README links by content hash.
    readme = os.path.join(os.path.dirname(__file__), "..", "README.md")
    text = open(readme).read()
    text = re.sub(r"(assets/card-(?:dark|light)\.svg)(\?v=[0-9a-f]+)?", rf"\1?v={digest.hexdigest()[:10]}", text)
    with open(readme, "w") as f:
        f.write(text)


if __name__ == "__main__":
    main()
