"""Generate the animated terminal profile card (dark + light SVG) from live GitHub data.

Standard library only. Reads GITHUB_TOKEN from the environment, or falls back to `gh auth token`.
Usage: python3 scripts/generate.py [login]
"""
import datetime as dt
import html
import json
import math
import os
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
    "dark": dict(bg="#0b0d10", border="#21262d", text="#e6edf3", dim="#7d8590", accent="#3fb950",
                 chrome="#30363d", off="#161b22", heat=["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]),
    "light": dict(bg="#fbfbfb", border="#d8dee4", text="#1f2328", dim="#6e7781", accent="#1a7f37",
                  chrome="#d0d7de", off="#eaeef2", heat=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]),
}

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
CW = 8.4  # monospace advance at 14px, used only for sizing typed clips


def vol(x, y):
    """Toy implied-vol surface. x: log-moneyness in [-1, 1], y: maturity in [-1, 1], short to long."""
    t = (y + 1) / 2
    return 0.75 * x * x * math.exp(-1.4 * t) - 0.28 * x * math.exp(-1.0 * t) + 0.22 * t - 0.30


def surface_frames(box, n=48, lines=11, samples=18, tilt=0.62, dist=3.4, swing=0.75):
    """Project the surface mesh while it rocks +-swing radians, and fit every frame into one shared box.

    box: (x0, y0, x1, y1). Returns, per frame, three SVG path strings bucketed far, mid, near.
    """
    cb, sb = math.cos(tilt), math.sin(tilt)
    grid = [-1 + 2 * i / (lines - 1) for i in range(lines)]
    ts = [-1 + 2 * i / (samples - 1) for i in range(samples)]
    raw = []
    for f in range(n):
        a = 0.55 + swing * math.sin(2 * math.pi * f / n)
        ca, sa = math.cos(a), math.sin(a)
        polys = []
        for g in grid:
            for along_x in (True, False):
                pts, depth = [], 0.0
                for s in ts:
                    x, y = (s, g) if along_x else (g, s)
                    z = vol(x, y)
                    x1, y1 = x * ca - y * sa, x * sa + y * ca
                    d, zz = y1 * cb - z * sb, y1 * sb + z * cb
                    k = 1.0 / (d + dist)
                    pts.append((k * x1, -k * zz))
                    depth += d
                polys.append((pts, depth / len(ts)))
        raw.append(polys)
    xs = [p[0] for fr in raw for pts, _ in fr for p in pts]
    ys = [p[1] for fr in raw for pts, _ in fr for p in pts]
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / (max(xs) - min(xs)), (y1 - y0) / (max(ys) - min(ys)))
    ox = x0 + ((x1 - x0) - s * (max(xs) - min(xs))) / 2 - s * min(xs)
    oy = y0 + ((y1 - y0) - s * (max(ys) - min(ys))) / 2 - s * min(ys)
    frames = []
    for fr in raw:
        buckets = ["", "", ""]
        for pts, depth in fr:
            b = 0 if depth > 0.45 else (1 if depth > -0.45 else 2)
            buckets[b] += "M" + " ".join(f"{ox + s * px:.0f},{oy + s * py:.0f}" for px, py in pts)
        frames.append(buckets)
    return frames


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
.fr{{visibility:hidden;animation:fr 7.2s steps(1) infinite}}
@keyframes fr{{0%{{visibility:visible}}2.08%{{visibility:hidden}}}}
.cur{{fill:{p["text"]};animation:k 1.1s steps(1) infinite}}
@keyframes k{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;clip-path:none!important}} .f0{{visibility:visible!important}}}}
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
    # spinning implied-vol surface in the neofetch logo slot
    frames = surface_frames((36, 92, 262, 286))
    n, period = len(frames), 7.2
    step = period / n
    out.append(f'<g class="r" style="animation-delay:1.0s" fill="none" stroke="{p["accent"]}" stroke-width="1" stroke-linejoin="round">')
    for i, buckets in enumerate(frames):
        out.append(f'<g class="fr{" f0" if i == 0 else ""}" style="animation-delay:{i * step - period:.2f}s">')
        for d, op in zip(buckets, (0.32, 0.62, 1)):
            if d:
                out.append(f'<path d="{d}" stroke-opacity="{op}"/>')
        out.append('</g>')
    out.append('</g>')
    out.append(f'<text class="r d" style="font-size:11px;animation-delay:1.0s" x="36" y="{y0 + 44 + 7 * 26 - 26}">σ(k, τ)</text>')

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
    for theme in PALETTES:
        path = os.path.join(OUT, f"card-{theme}.svg")
        with open(path, "w") as f:
            f.write(render(theme, since, total, weeks) + "\n")
        print("wrote", os.path.normpath(path))


if __name__ == "__main__":
    main()
