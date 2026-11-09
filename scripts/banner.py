"""Generate the profile banner (assets/banner.svg): a dark Caelion-family card with an animated
market pipeline on the left and a planet horizon with an orbiting satellite on the right.

Standard library only, deterministic (seeded star field). Usage: python3 scripts/banner.py
"""
import hashlib
import math
import os
import random
import re

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "banner.svg")
W, H = 1700, 540
X0 = 92  # left text column

NAME = "AARAV MAHAJAN"
KICKER = "CO-FOUNDER  ·  CAELION CAPITAL"
HEAD = ("Systems for markets,", "built from first principles.")
SUB = "Quant research and market infrastructure for Indian equities, in Python, C++ and TypeScript."
STAGES = ["TICK", "BOOK", "SIGNAL", "RISK", "FILL"]
RULES = "POINT-IN-TIME DATA  ·  DETERMINISTIC PATHS  ·  REPORT THE NULL"

SERIF = "Georgia, 'Iowan Old Style', 'Times New Roman', serif"
SANS = "-apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, monospace"

# Planet: a huge sphere whose limb crosses the right half of the card.
PCX, PCY, PR = 1330, 1390, 1010
# Satellite orbit, an ellipse tilted around the planet's visible limb.
OCX, OCY, ORX, ORY, OTILT = 1330, 372, 300, 64, -11


def stars(rng, n=150):
    out = []
    for i in range(n):
        x = rng.uniform(760, W - 30)
        y = rng.uniform(26, H - 30)
        if math.hypot(x - PCX, y - PCY) < PR + 6:  # nothing in front of the planet
            continue
        r = rng.choice([0.6, 0.7, 0.8, 0.9, 1.1, 1.4]) if rng.random() < 0.93 else rng.uniform(1.6, 2.1)
        a = rng.uniform(0.18, 0.75)
        tw = ""
        if rng.random() < 0.22:  # a few twinkle, each on its own clock
            dur = rng.uniform(3.5, 8.0)
            tw = (f'<animate attributeName="opacity" values="{a:.2f};{a * 0.25:.2f};{a:.2f}" '
                  f'dur="{dur:.1f}s" begin="{-rng.uniform(0, dur):.1f}s" repeatCount="indefinite"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="#fff" opacity="{a:.2f}">{tw}</circle>')
    return "\n    ".join(out)


def ellipse_path(cx, cy, rx, ry, tilt):
    """Closed path for an ellipse (two arcs), clockwise from the leftmost point, rotated by tilt degrees."""
    t = math.radians(tilt)
    def p(a):
        x, y = rx * math.cos(a), ry * math.sin(a)
        return cx + x * math.cos(t) - y * math.sin(t), cy + x * math.sin(t) + y * math.cos(t)
    (ax, ay), (bx, by) = p(math.pi), p(0)
    return (f"M{ax:.1f},{ay:.1f} A{rx},{ry} {tilt} 1 1 {bx:.1f},{by:.1f} "
            f"A{rx},{ry} {tilt} 1 1 {ax:.1f},{ay:.1f}Z")


def pipeline(y=468):
    gap = 152
    xs = [X0 + 8 + i * gap for i in range(len(STAGES))]
    parts = [f'<line x1="{xs[0]}" y1="{y}" x2="{xs[-1]}" y2="{y}" stroke="#ffffff" stroke-opacity="0.14"/>']
    for x, name in zip(xs, STAGES):
        parts.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="#050507" stroke="#ffffff" stroke-opacity="0.55" stroke-width="1.2"/>')
        parts.append(f'<text x="{x}" y="{y + 32}" text-anchor="middle" class="mono label">{name}</text>')
    # A packet travels stage to stage, resting at each one, then the loop restarts.
    n = len(xs)
    vals, keys = [], []
    for i, x in enumerate(xs):
        t0, t1 = i / n, i / n + 0.6 / n
        vals += [x, x]
        keys += [t0, t1]
    vals.append(xs[0])
    keys.append(1.0)
    keys = [round(k, 4) for k in keys]
    v = ";".join(str(x) for x in vals)
    k = ";".join(str(t) for t in keys)
    parts.append(f'<circle cy="{y}" r="4.6" fill="#fff" filter="url(#glow)">'
                 f'<animate attributeName="cx" values="{v}" keyTimes="{k}" dur="9s" repeatCount="indefinite" '
                 f'calcMode="spline" keySplines="{";".join(["0.4 0 0.2 1"] * (len(keys) - 1))}"/></circle>')
    # The last hop back to the start would sweep through every stage, so hide it.
    parts[-1] = parts[-1].replace('</circle>', f'<animate attributeName="opacity" values="1;1;0;0" '
                                               f'keyTimes="0;{keys[-2]};{(keys[-2] + 1) / 2:.4f};1" dur="9s" repeatCount="indefinite"/></circle>')
    return "\n  ".join(parts)


def glyph(x, y):
    """Caelion constellation mark, small: four stars on a bent line."""
    pts = [(x, y), (x + 9, y + 6), (x + 10, y + 22), (x + 15, y + 33)]
    line = " ".join(f"{a},{b}" for a, b in pts)
    dots = "".join(f'<circle cx="{a}" cy="{b}" r="{r}" fill="#fff"/>' for (a, b), r in zip(pts, (1.6, 1.6, 2.4, 1.8)))
    return f'<polyline points="{line}" fill="none" stroke="#fff" stroke-opacity="0.45" stroke-width="0.9"/>{dots}'


def main():
    rng = random.Random(69)
    orbit = ellipse_path(OCX, OCY, ORX, ORY, OTILT)
    cols = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>' for x in range(40, W, 66))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
  aria-label="Aarav Mahajan. {HEAD[0]} {HEAD[1]} {SUB}">
<defs>
  <clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>
  <radialGradient id="air" cx="{PCX}" cy="{PCY}" r="{PR + 90}" gradientUnits="userSpaceOnUse">
    <stop offset="{PR / (PR + 90):.4f}" stop-color="#a87cf0" stop-opacity="0.30"/>
    <stop offset="{(PR + 18) / (PR + 90):.4f}" stop-color="#7d5fd0" stop-opacity="0.10"/>
    <stop offset="1" stop-color="#a87cf0" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="body" cx="{PCX - 120}" cy="{PCY - PR + 40}" r="{PR}" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#17141f"/>
    <stop offset="0.35" stop-color="#0a0910"/>
    <stop offset="1" stop-color="#050507"/>
  </radialGradient>
  <linearGradient id="limb" x1="700" y1="0" x2="{W}" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset="0.45" stop-color="#e9e2ff" stop-opacity="0.55"/>
    <stop offset="0.8" stop-color="#fff" stop-opacity="0.85"/>
    <stop offset="1" stop-color="#e9e2ff" stop-opacity="0.35"/>
  </linearGradient>
  <linearGradient id="shade" x1="0" y1="0" x2="{W}" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#050507" stop-opacity="1"/>
    <stop offset="0.42" stop-color="#050507" stop-opacity="0.9"/>
    <stop offset="0.62" stop-color="#050507" stop-opacity="0"/>
  </linearGradient>
  <filter id="glow" x="-200%" y="-200%" width="500%" height="500%">
    <feGaussianBlur stdDeviation="3.2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="14"/></filter>
  <style>
    .mono {{ font-family: {MONO}; }}
    .label {{ font-size: 14px; letter-spacing: 2.6px; fill: #9a9aa3; }}
  </style>
</defs>
<g clip-path="url(#card)">
  <rect width="{W}" height="{H}" fill="#050507"/>
  <g stroke="#ffffff" stroke-opacity="0.022">{cols}</g>
  <g>
    {stars(rng)}
  </g>
  <!-- Planet: atmosphere, body, lit limb -->
  <circle cx="{PCX}" cy="{PCY}" r="{PR + 90}" fill="url(#air)"/>
  <circle cx="{PCX}" cy="{PCY}" r="{PR + 26}" fill="none" stroke="#a87cf0" stroke-opacity="0.16" stroke-width="22" filter="url(#soft)"/>
  <circle cx="{PCX}" cy="{PCY}" r="{PR}" fill="url(#body)"/>
  <circle cx="{PCX}" cy="{PCY}" r="{PR}" fill="none" stroke="url(#limb)" stroke-width="1.4"/>
  <!-- Orbit and satellite -->
  <path d="{orbit}" fill="none" stroke="#ffffff" stroke-opacity="0.13" stroke-dasharray="2 6"/>
  <g filter="url(#glow)">
    <circle r="3.4" fill="#fff">
      <animateMotion dur="22s" repeatCount="indefinite" path="{orbit}"/>
    </circle>
  </g>
  <circle r="11" fill="#a87cf0" opacity="0.18">
    <animateMotion dur="22s" repeatCount="indefinite" path="{orbit}"/>
  </circle>
  <!-- Keep the text column clean -->
  <rect width="{W}" height="{H}" fill="url(#shade)"/>

  <!-- Wordmark -->
  <g transform="translate({X0 - 2},{70})">{glyph(0, 0)}</g>
  <text x="{X0 + 34}" y="{100}" font-family="{SANS}" font-size="22" font-weight="600" letter-spacing="5.2" fill="#f4f4f6">{NAME}</text>

  <!-- Kicker -->
  <line x1="{X0}" y1="{170}" x2="{X0 + 44}" y2="{170}" stroke="#ffffff" stroke-opacity="0.35"/>
  <text x="{X0 + 62}" y="{175}" class="mono" font-size="15" letter-spacing="3.4" fill="#9a9aa3">{KICKER}</text>

  <!-- Headline -->
  <text x="{X0 - 3}" y="{262}" font-family="{SERIF}" font-size="70" fill="#f6f6f8" letter-spacing="-0.6">{HEAD[0]}</text>
  <text x="{X0 - 3}" y="{340}" font-family="{SERIF}" font-size="70" font-style="italic" fill="#8c8c95" letter-spacing="-0.6">{HEAD[1]}</text>
  <text x="{X0}" y="{392}" font-family="{SANS}" font-size="20" fill="#a9a9b2">{SUB}</text>

  <!-- Pipeline -->
  {pipeline()}

  <!-- Rules -->
  <text x="{W - 64}" y="{H - 40}" text-anchor="end" class="mono" font-size="13" letter-spacing="2.4" fill="#6f6f79">{RULES}</text>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="22" fill="none" stroke="#ffffff" stroke-opacity="0.07"/>
</svg>
'''
    with open(OUT, "w") as f:
        f.write(svg)
    # GitHub's image CDN caches by URL, so version the README link by content hash.
    readme = os.path.join(os.path.dirname(__file__), "..", "README.md")
    text = open(readme).read()
    v = hashlib.sha256(svg.encode()).hexdigest()[:10]
    text = re.sub(r"(assets/banner\.svg)(\?v=[0-9a-f]+)?", rf"\1?v={v}", text)
    with open(readme, "w") as f:
        f.write(text)
    print(os.path.normpath(OUT), len(svg), "bytes, v=" + v)


if __name__ == "__main__":
    main()
