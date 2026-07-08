#!/usr/bin/env python3
"""Generate a self-hosted GitHub "scorecard" as a static SVG.

Runs in CI with the built-in GITHUB_TOKEN and writes an SVG committed to the
`output` branch, so the profile README never depends on a live third-party
stats server at render time. Public data only.

Design: an editorial scorecard, not a stat-tile card. A grade dial (throughput-
weighted rank), a ledger of the year's contribution activity, and a language
breakdown — tokyonight palette, monospace numerals, hairline structure, to sit
with bjorkslefteyelash.com/api/nowplaying.svg.
"""
import json
import math
import os
import sys
import time
import urllib.request

LOGIN = os.environ.get("STATS_LOGIN", "cupidthatbtc")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist/github-stats-dark.svg"

# ---- palette (tokyonight; matches the now-playing card) -------------------
BG, PANEL = "#1a1b27", "#1e2030"
HAIR = "#292e42"          # hairlines / tracks
INK = "#c0caf5"           # bright numerals
TXT = "#a9b1d6"           # labels
DIM = "#565f89"           # small-caps kickers, muted
BLUE = "#7aa2f7"
PURPLE = "#bb9af7"
GREEN = "#9ece6a"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,'SF Mono','JetBrains Mono','Cascadia Code',Menlo,Consolas,monospace"

QUERY = """
query($login:String!){
  user(login:$login){
    login
    followers{totalCount}
    repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
      totalCount
      nodes{
        stargazerCount
        languages(first:12, orderBy:{field:SIZE, direction:DESC}){
          edges{ size node{ name color } }
        }
      }
    }
    contributionsCollection{
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ contributionCount date } }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": f"{LOGIN}-scorecard"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def commas(n):
    return f"{n:,}"


def streaks(days):
    longest = run = 0
    for d in days:
        if d["contributionCount"] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    cur, i = 0, len(days) - 1
    if days and days[i]["contributionCount"] == 0:   # today may have no commit yet
        i -= 1
    while i >= 0 and days[i]["contributionCount"] > 0:
        cur += 1
        i -= 1
    return cur, longest


def grade(commits, prs, issues, longest):
    """Throughput-weighted contribution rank. Measures activity, not popularity:
    stars/followers are deliberately excluded so a pseudonymous account isn't
    graded on vanity metrics it never chases. Reference medians are calibrated to
    an active solo contributor."""
    def cdf(x):    # exponential CDF — saturates as activity climbs
        return 1 - 2 ** (-x)
    terms = [
        (commits, 800, 3.0, cdf),
        (prs,      50, 3.0, cdf),
        (issues,   25, 1.5, cdf),
        (longest,  21, 1.5, cdf),
    ]
    score = sum(w * f(v / m) for v, m, w, f in terms) / sum(w for *_, w, _ in terms)
    pct = 100 * (1 - score)                       # lower is better
    thresholds = [(1, "S"), (12.5, "A+"), (25, "A"), (37.5, "A-"), (50, "B+"),
                  (62.5, "B"), (75, "B-"), (87.5, "C+"), (100, "C")]
    letter = next(l for t, l in thresholds if pct <= t)
    return letter, pct, score


# ---------------------------------------------------------------------------
def build():
    u = fetch()
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    repos = u["repositories"]["nodes"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]

    commits = cc["totalCommitContributions"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]
    stars = sum(r["stargazerCount"] for r in repos)
    followers = u["followers"]["totalCount"]
    repo_n = u["repositories"]["totalCount"]
    total = cal["totalContributions"]
    cur, longest = streaks(days)
    letter, pct, score = grade(commits, prs, issues, longest)

    lang_bytes, lang_color = {}, {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            lang_bytes[n] = lang_bytes.get(n, 0) + e["size"]
            lang_color[n] = e["node"]["color"] or "#8a8a8a"
    lt = sum(lang_bytes.values()) or 1
    langs = [(n, b / lt * 100) for n, b in
             sorted(lang_bytes.items(), key=lambda kv: -kv[1]) if b / lt * 100 >= 0.5][:4]

    W, H = 820, 308
    P = 26
    s = []
    A = s.append

    A(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'xmlns="http://www.w3.org/2000/svg" role="img" '
      f'aria-label="GitHub scorecard for {esc(u["login"])} — rank {letter}">')
    A('<defs>'
      f'<linearGradient id="arc" x1="0" y1="0" x2="1" y2="1">'
      f'<stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{PURPLE}"/>'
      f'</linearGradient></defs>')
    A(f'<style>text{{font-family:{SANS};}} .m{{font-family:{MONO};}} '
      f'.k{{fill:{DIM};font-size:10px;letter-spacing:1.6px;}} '
      f'.lab{{fill:{TXT};font-size:12.5px;}}</style>')
    A(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" '
      f'fill="{BG}" stroke="{HAIR}"/>')

    # ---- header -----------------------------------------------------------
    A(f'<text x="{P}" y="34" fill="{INK}" font-size="17" font-weight="600">'
      f'{esc(u["login"])}<tspan fill="{DIM}" font-weight="400"> / scorecard</tspan></text>')
    A(f'<text x="{W-P}" y="33" class="k" text-anchor="end">'
      f'GITHUB · LAST 12 MONTHS</text>')
    A(f'<line x1="{P}" y1="50" x2="{W-P}" y2="50" stroke="{HAIR}"/>')

    top, bot = 50, 264
    zx1, zx2 = 266, 548          # vertical zone dividers
    A(f'<line x1="{zx1}" y1="{top+14}" x2="{zx1}" y2="{bot-14}" stroke="{HAIR}"/>')
    A(f'<line x1="{zx2}" y1="{top+14}" x2="{zx2}" y2="{bot-14}" stroke="{HAIR}"/>')

    # ---- zone A: grade dial ----------------------------------------------
    cx, cy, R, sw = 132, 156, 53, 9
    C = 2 * math.pi * R
    frac = max(0.04, (100 - pct) / 100)
    A(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{HAIR}" stroke-width="{sw}"/>')
    A(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="url(#arc)" '
      f'stroke-width="{sw}" stroke-linecap="round" '
      f'stroke-dasharray="{frac*C:.2f} {C:.2f}" '
      f'transform="rotate(-90 {cx} {cy})"/>')
    A(f'<text x="{cx}" y="{cy+2}" class="m" fill="{INK}" font-size="46" '
      f'font-weight="700" text-anchor="middle">{letter}</text>')
    A(f'<text x="{cx}" y="{cy+25}" fill="{DIM}" font-size="10" '
      f'text-anchor="middle" letter-spacing="2">RANK</text>')
    A(f'<text x="{cx}" y="{bot-16}" fill="{TXT}" font-size="12.5" text-anchor="middle">'
      f'top <tspan class="m" fill="{INK}">{round(pct)}%</tspan> by activity</text>')

    # ---- zone B: ledger ---------------------------------------------------
    bx, bxr = zx1 + 24, zx2 - 22
    def ledger(y, label, value, accent=INK):
        s.append(f'<text x="{bx}" y="{y}" class="lab">{label}</text>')
        s.append(f'<text x="{bxr}" y="{y}" class="m" fill="{accent}" font-size="14.5" '
                 f'text-anchor="end">{value}</text>')
        s.append(f'<line x1="{bx}" y1="{y+9}" x2="{bxr}" y2="{y+9}" stroke="#20233a"/>')

    A(f'<text x="{bx}" y="{top+22}" class="k">THROUGHPUT</text>')
    ry = top + 42
    for lab, val in [("commits", commas(commits)),
                     ("pull requests", commas(prs)),
                     ("issues", commas(issues))]:
        ledger(ry, lab, val)
        ry += 26
    A(f'<text x="{bx}" y="{ry+6}" class="k">CONSISTENCY</text>')
    ry += 28
    for lab, val, ac in [("current streak", f"{cur}d", GREEN if cur else DIM),
                         ("longest streak", f"{longest}d", INK),
                         ("total contributions", commas(total), INK)]:
        ledger(ry, lab, val, ac)
        ry += 26

    # ---- zone C: languages -----------------------------------------------
    cx0, cxr = zx2 + 24, W - P
    A(f'<text x="{cx0}" y="{top+22}" class="k">LANGUAGES</text>')
    ly = top + 48
    barx, barw = cx0, cxr - cx0
    for name, p in langs:
        s.append(f'<circle cx="{cx0+4}" cy="{ly-4}" r="4" fill="{lang_color[name]}"/>')
        s.append(f'<text x="{cx0+15}" y="{ly}" class="lab">{esc(name)}</text>')
        s.append(f'<text x="{cxr}" y="{ly}" class="m" fill="{TXT}" font-size="12" '
                 f'text-anchor="end">{p:.0f}%</text>')
        s.append(f'<rect x="{barx}" y="{ly+8}" width="{barw}" height="5" rx="2.5" fill="{HAIR}"/>')
        w = max(4, barw * p / 100)
        s.append(f'<rect x="{barx}" y="{ly+8}" width="{w:.1f}" height="5" rx="2.5" '
                 f'fill="{lang_color[name]}"/>')
        ly += 36

    # ---- footer strip -----------------------------------------------------
    A(f'<line x1="{P}" y1="{bot}" x2="{W-P}" y2="{bot}" stroke="{HAIR}"/>')
    fy = bot + 30
    A(f'<text x="{P}" y="{fy}" fill="{TXT}" font-size="12">'
      f'<tspan class="m" fill="{INK}">{repo_n}</tspan> public repos'
      f'<tspan fill="{DIM}">   ·   </tspan>'
      f'<tspan class="m" fill="{INK}">{stars}</tspan> stars'
      f'<tspan fill="{DIM}">   ·   </tspan>'
      f'<tspan class="m" fill="{INK}">{followers}</tspan> followers</text>')
    A(f'<text x="{W-P}" y="{fy}" fill="{DIM}" font-size="11" text-anchor="end">'
      f'updated {time.strftime("%b %-d, %Y", time.gmtime())}</text>')

    A('</svg>')
    return "\n".join(s)


if __name__ == "__main__":
    svg = build()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes)")
