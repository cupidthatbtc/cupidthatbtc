#!/usr/bin/env python3
"""Generate a self-hosted stats.fm "listening" card as a static SVG.

The music twin of the GitHub scorecard: same frame + typography, green accent to
match bjorkslefteyelash.com/api/nowplaying.svg (the other stats.fm-powered part).
Runs in CI, committed to the `output` branch, so the README never depends on a
live third-party at render time. Public stats.fm data only.
"""
import json
import os
import sys
import time
import urllib.request

USER = os.environ.get("STATSFM_USER", "cupidthatbtc")
RANGE = os.environ.get("STATSFM_RANGE", "weeks")
RANGE_LABEL = {"weeks": "LAST 4 WEEKS", "months": "LAST 6 MONTHS", "lifetime": "ALL TIME"}[RANGE]
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist/listening-dark.svg"

# ---- palette (now-playing card: green accent on tokyonight) ---------------
BG = "#1a1b27"
HAIR = "#292e42"
INK = "#c0caf5"
TXT = "#a9b1d6"
DIM = "#565f89"
GREEN = "#9ece6a"
TRACK = "#252a3d"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,'SF Mono','JetBrains Mono','Cascadia Code',Menlo,Consolas,monospace"


def api(path):
    req = urllib.request.Request("https://api.stats.fm/api/v1/" + path,
                                 headers={"User-Agent": f"{USER}-listening-card"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)["items"]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def commas(n):
    return f"{n:,}"


def clip(s, n):
    return s if len(s) <= n else s[:n - 1] + "…"


def build():
    stats = api(f"users/{USER}/streams/stats?range={RANGE}")
    artists = api(f"users/{USER}/top/artists?range={RANGE}&limit=5")
    top_track = api(f"users/{USER}/top/tracks?range={RANGE}&limit=1")[0]

    streams = stats["count"]
    hours = round(stats["durationMs"] / 3600000)
    rows = [(a["artist"]["name"], a.get("streams", 0), round(a.get("playedMs", 0) / 60000))
            for a in artists]
    top = rows[0]
    maxmin = max((m for _, _, m in rows), default=1) or 1
    tt = f'{clip(top_track["track"]["name"], 22)} — {top_track["track"]["artists"][0]["name"]}'

    W, H, P = 820, 278, 30
    s = []
    A = s.append
    A(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
      f'role="img" aria-label="stats.fm listening card for {esc(USER)} — top artist {esc(top[0])}">')
    A(f'<style>text{{font-family:{SANS};}} .m{{font-family:{MONO};}} '
      f'.k{{fill:{DIM};font-size:9.5px;letter-spacing:2px;}} .lab{{fill:{TXT};font-size:12.5px;}}</style>')
    A(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="{BG}" stroke="{HAIR}"/>')

    # ---- masthead ---------------------------------------------------------
    A(f'<text x="{P}" y="35" fill="{INK}" font-size="16.5" font-weight="600">'
      f'{esc(USER)}<tspan fill="{DIM}" font-weight="400"> / listening</tspan></text>')
    A(f'<text x="{W-P}" y="34" class="k" text-anchor="end">STATS.FM · {RANGE_LABEL}</text>')
    A(f'<line x1="{P}" y1="50" x2="{W-P}" y2="50" stroke="{HAIR}"/>')

    # ---- left: #1 artist hero --------------------------------------------
    A(f'<text x="{P}" y="78" class="k">ON HEAVY ROTATION</text>')
    A(f'<text x="{P}" y="128" fill="{INK}" font-size="38" font-weight="800" '
      f'letter-spacing="-0.5">{esc(clip(top[0], 15))}</text>')
    A(f'<rect x="{P+2}" y="140" width="52" height="3" rx="1.5" fill="{GREEN}"/>')
    A(f'<text x="{P}" y="168" class="m" fill="{TXT}" font-size="13">'
      f'{commas(top[1])} plays<tspan fill="{DIM}">  ·  </tspan>{commas(top[2])} min</text>')
    A(f'<text x="{P}" y="192" fill="{DIM}" font-size="10.5">most-played track · '
      f'<tspan fill="{TXT}">{esc(tt)}</tspan></text>')

    # ---- right: top artists by time --------------------------------------
    lx, lxr = 392, W - P
    bx0, bx1 = 556, 720
    A(f'<line x1="366" y1="64" x2="366" y2="214" stroke="{HAIR}"/>')
    A(f'<text x="{lx}" y="78" class="k">TOP ARTISTS · BY TIME</text>')
    ry = 100
    for i, (name, plays, mins) in enumerate(rows, 1):
        A(f'<text x="{lx}" y="{ry}" class="m" fill="{DIM}" font-size="11">{i}</text>')
        A(f'<text x="{lx+18}" y="{ry}" class="lab">{esc(clip(name, 16))}</text>')
        A(f'<rect x="{bx0}" y="{ry-9}" width="{bx1-bx0}" height="7" rx="3" fill="{TRACK}"/>')
        w = max(4, (bx1 - bx0) * mins / maxmin)
        A(f'<rect x="{bx0}" y="{ry-9}" width="{w:.1f}" height="7" rx="3" fill="{GREEN}" '
          f'fill-opacity="{0.95 if i == 1 else 0.6}"/>')
        A(f'<text x="{lxr}" y="{ry}" class="m" fill="{INK if i==1 else TXT}" font-size="12.5" '
          f'text-anchor="end">{commas(mins)}m</text>')
        A(f'<line x1="{lx}" y1="{ry+8}" x2="{lxr}" y2="{ry+8}" stroke="{HAIR}" stroke-opacity="0.5"/>')
        ry += 20

    # ---- summary band -----------------------------------------------------
    A(f'<line x1="{P}" y1="226" x2="{W-P}" y2="226" stroke="{HAIR}"/>')
    A(f'<text x="{P}" y="256" fill="{TXT}" font-size="12">'
      f'<tspan class="m" fill="{INK}">{commas(streams)}</tspan> streams'
      f'<tspan fill="{DIM}">   ·   </tspan><tspan class="m" fill="{INK}">{commas(hours)}</tspan> hours listened'
      f'<tspan fill="{DIM}">   ·   </tspan>bars show minutes played</text>')
    A(f'<text x="{W-P}" y="256" fill="{DIM}" font-size="10.5" text-anchor="end">'
      f'updated {time.strftime("%b %-d, %Y", time.gmtime())}</text>')

    A('</svg>')
    return "\n".join(s)


if __name__ == "__main__":
    svg = build()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes)")
