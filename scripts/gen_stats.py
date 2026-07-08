#!/usr/bin/env python3
"""Generate a self-hosted GitHub stats card as a static SVG.

Runs in CI with the built-in GITHUB_TOKEN and writes an SVG that is committed
to the `output` branch, so the profile README never depends on a live
third-party stats server at render time. Public data only.

Styled to match bjorkslefteyelash.com/api/nowplaying.svg (tokyonight card).
"""
import json
import os
import sys
import time
import urllib.request

LOGIN = os.environ.get("STATS_LOGIN", "cupidthatbtc")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist/github-stats-dark.svg"

# tokyonight palette (matches the now-playing card)
BG, BORDER = "#1a1b27", "#292e42"
TITLE = "#7aa2f7"       # accent blue
NUM = "#c0caf5"         # bright numbers
LABEL = "#565f89"       # dim labels
TEXT = "#a9b1d6"        # secondary
TRACK = "#292e42"       # bar background
OTHER = "#414868"       # remainder segment
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

QUERY = """
query($login:String!){
  user(login:$login){
    login
    followers{totalCount}
    contributionsCollection{
      totalCommitContributions
      totalPullRequestContributions
    }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
      totalCount
      nodes{
        stargazerCount
        languages(first:12, orderBy:{field:SIZE, direction:DESC}){
          edges{ size node{ name color } }
        }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": f"{LOGIN}-stats-card",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def comma(n):
    return f"{n:,}"


def build():
    u = fetch()
    cc = u["contributionsCollection"]
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)

    lang_bytes, lang_color = {}, {}
    for r in repos:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            lang_bytes[name] = lang_bytes.get(name, 0) + e["size"]
            lang_color[name] = e["node"]["color"] or "#8a8a8a"
    total = sum(lang_bytes.values()) or 1
    ranked = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)
    top = [(n, b / total * 100) for n, b in ranked if b / total * 100 >= 0.5][:5]

    tiles = [
        (comma(cc["totalCommitContributions"]), "commits"),
        (comma(cc["totalPullRequestContributions"]), "pull reqs"),
        (comma(u["repositories"]["totalCount"]), "repos"),
        (comma(u["followers"]["totalCount"]), "followers"),
    ]

    W, H = 480, 212
    P = 20
    updated = time.strftime("%b %d, %Y", time.gmtime())
    parts = [
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="GitHub stats for {esc(u["login"])}">',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" '
        f'fill="{BG}" stroke="{BORDER}"/>',
        f'<style>text{{font-family:{FONT};}}</style>',
        # header
        f'<text x="{P}" y="33" fill="{TITLE}" font-size="15.5" '
        f'font-weight="600">{esc(u["login"])}</text>',
        f'<text x="{W-P}" y="32" fill="{LABEL}" font-size="10.5" '
        f'text-anchor="end">GitHub · {updated}</text>',
        f'<line x1="{P}" y1="47" x2="{W-P}" y2="47" stroke="{BORDER}"/>',
    ]

    # stat tiles
    col_w = (W - 2 * P) / 4
    for i, (val, lab) in enumerate(tiles):
        cx = P + col_w * (i + 0.5)
        parts.append(
            f'<text x="{cx:.1f}" y="92" fill="{NUM}" font-size="23" '
            f'font-weight="700" text-anchor="middle">{val}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="109" fill="{LABEL}" font-size="10.5" '
            f'text-anchor="middle" letter-spacing="0.4">{lab}</text>'
        )

    # languages
    parts.append(
        f'<text x="{P}" y="140" fill="{LABEL}" font-size="10.5" '
        f'letter-spacing="1.4">LANGUAGES</text>'
    )
    bar_x, bar_y, bar_w, bar_h = P, 150, W - 2 * P, 12
    parts.append(
        f'<clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" '
        f'height="{bar_h}" rx="6"/></clipPath>'
    )
    parts.append(
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" '
        f'rx="6" fill="{TRACK}"/>'
    )
    parts.append(f'<g clip-path="url(#bar)">')
    x = bar_x
    for name, pct in top:
        seg = bar_w * pct / 100
        parts.append(
            f'<rect x="{x:.2f}" y="{bar_y}" width="{seg:.2f}" '
            f'height="{bar_h}" fill="{lang_color[name]}"/>'
        )
        x += seg
    if x < bar_x + bar_w - 0.5:
        parts.append(
            f'<rect x="{x:.2f}" y="{bar_y}" width="{bar_x + bar_w - x:.2f}" '
            f'height="{bar_h}" fill="{OTHER}"/>'
        )
    parts.append("</g>")

    # legend chips
    lx, ly = P, 188
    for name, pct in top:
        parts.append(
            f'<circle cx="{lx+4}" cy="{ly-4}" r="4.5" '
            f'fill="{lang_color[name]}"/>'
        )
        label = f"{esc(name)} {round(pct)}%"
        parts.append(
            f'<text x="{lx+14}" y="{ly}" fill="{TEXT}" '
            f'font-size="11.5">{label}</text>'
        )
        lx += 14 + len(label) * 6.7 + 16

    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    svg = build()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes)")
