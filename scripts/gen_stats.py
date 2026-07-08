#!/usr/bin/env python3
"""Generate a self-hosted GitHub "scorecard" as a static SVG.

Runs in CI with the built-in GITHUB_TOKEN, writes an SVG committed to the
`output` branch, so the profile README never depends on a live third-party
stats server at render time. Public data only.

Concept: cupidthatbtc models bounded *score distributions* (album ratings). So
his GitHub year is scored the same way — the rank isn't a mystery letter in a
gauge, it's a visible position on the (genuinely heavy-tailed) distribution of
contributor activity. tokyonight palette, flat color, monospace numerals, to sit
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
BG = "#1a1b27"
HAIR = "#282c40"          # hairlines / tracks
FAINT = "#20233440"       # faint row rules
INK = "#c8d3f5"           # bright / numerals
TXT = "#a9b1d6"           # labels
DIM = "#565f89"           # kickers, muted
BLUE = "#7aa2f7"          # single accent
CURVE = "#2d3459"         # muted density body
RIDGE = "#5b6aa8"         # density outline
TAIL = "#7aa2f7"          # highlighted tail (the top slice)
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
      nodes{ stargazerCount languages(first:12, orderBy:{field:SIZE, direction:DESC}){
        edges{ size node{ name color } } } }
    }
    contributionsCollection{
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount } } }
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
    if days and days[i]["contributionCount"] == 0:
        i -= 1
    while i >= 0 and days[i]["contributionCount"] > 0:
        cur += 1
        i -= 1
    return cur, longest


def grade(commits, prs, issues, longest):
    """Throughput-weighted percentile → letter. Measures activity, not
    popularity: stars/followers are excluded so a pseudonymous account isn't
    graded on vanity metrics. Reference medians for an active solo contributor."""
    def cdf(x):
        return 1 - 2 ** (-x)
    terms = [(commits, 800, 3.0), (prs, 50, 3.0), (issues, 25, 1.5), (longest, 21, 1.5)]
    score = sum(w * cdf(v / m) for v, m, w in terms) / sum(w for *_, w in terms)
    pct = 100 * (1 - score)
    thresholds = [(1, "S"), (12.5, "A+"), (25, "A"), (37.5, "A-"), (50, "B+"),
                  (62.5, "B"), (75, "B-"), (87.5, "C+"), (100, "C")]
    return next(l for t, l in thresholds if pct <= t), pct


def density_paths(x0, x1, base, h, pct):
    """A heavy-tailed reference curve (gamma f(x)=x^2 e^-x) with the tail beyond
    the user's quantile highlighted. Returns (body_path, tail_path, mx, my)."""
    N, XMAX = 170, 11.0
    xs = [XMAX * i / (N - 1) for i in range(N)]
    fs = [(x * x) * math.exp(-x) for x in xs]
    fmax = max(fs)
    tot = sum(fs)
    cum, c = [], 0.0
    for f in fs:
        c += f
        cum.append(c / tot)
    q = 1 - pct / 100.0
    mi = min(range(N), key=lambda i: abs(cum[i] - q))
    px = lambda i: x0 + xs[i] / XMAX * (x1 - x0)
    py = lambda i: base - fs[i] / fmax * h

    def area(lo):
        pts = " ".join(f"L{px(i):.1f} {py(i):.1f}" for i in range(lo, N))
        return f"M{px(lo):.1f} {base} {pts} L{px(N-1):.1f} {base} Z"

    ridge = f"M{px(0):.1f} {py(0):.1f} " + " ".join(f"L{px(i):.1f} {py(i):.1f}" for i in range(1, N))
    return area(0), area(mi), ridge, px(mi), py(mi)


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
    letter, pct = grade(commits, prs, issues, longest)

    lb, lc = {}, {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            lb[n] = lb.get(n, 0) + e["size"]
            lc[n] = e["node"]["color"] or "#8a8a8a"
    lt = sum(lb.values()) or 1
    langs = [(n, b / lt * 100) for n, b in sorted(lb.items(), key=lambda kv: -kv[1])
             if b / lt * 100 >= 0.5][:4]

    W, H, P = 820, 300, 30
    s = []
    A = s.append
    A(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
      f'role="img" aria-label="GitHub scorecard for {esc(u["login"])} — rank {letter}, '
      f'top {round(pct)}% by activity">')
    A(f'<style>text{{font-family:{SANS};}} .m{{font-family:{MONO};}} '
      f'.k{{fill:{DIM};font-size:9.5px;letter-spacing:2px;}} .lab{{fill:{TXT};font-size:12.5px;}}</style>')
    A(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="{BG}" stroke="{HAIR}"/>')

    # ---- masthead ---------------------------------------------------------
    A(f'<text x="{P}" y="35" fill="{INK}" font-size="16.5" font-weight="600">'
      f'{esc(u["login"])}<tspan fill="{DIM}" font-weight="400"> / scorecard</tspan></text>')
    A(f'<text x="{W-P}" y="34" class="k" text-anchor="end">'
      f'<tspan class="m" fill="{TXT}" letter-spacing="0">{followers}</tspan> FOLLOWERS'
      f'<tspan fill="{DIM}">  ·  </tspan>'
      f'<tspan class="m" fill="{TXT}" letter-spacing="0">{repo_n}</tspan> REPOS'
      f'<tspan fill="{DIM}">  ·  </tspan>'
      f'<tspan class="m" fill="{TXT}" letter-spacing="0">{stars}</tspan> STARS</text>')
    A(f'<line x1="{P}" y1="50" x2="{W-P}" y2="50" stroke="{HAIR}"/>')

    # ---- left: grade + distribution --------------------------------------
    A(f'<text x="{P}" y="76" class="k">ACTIVITY RANK</text>')
    A(f'<text x="{P}" y="150" fill="{INK}" font-size="78" font-weight="800" '
      f'letter-spacing="-2">{letter}</text>')
    gw = 46 if len(letter) == 1 else 74            # width the glyph(s) take
    A(f'<rect x="{P+2}" y="158" width="54" height="3" rx="1.5" fill="{BLUE}"/>')
    px0 = P + gw + 26
    A(f'<text x="{px0}" y="108" fill="{DIM}" font-size="12">top</text>')
    A(f'<text x="{px0}" y="140" class="m" fill="{INK}" font-size="30" '
      f'font-weight="700">{round(pct)}%</text>')
    A(f'<text x="{px0}" y="158" fill="{DIM}" font-size="11">by activity</text>')

    # distribution strip
    dx0, dx1, dbase, dh = P, 330, 232, 40
    A(f'<text x="{P}" y="188" class="k">WHERE YOU LAND · ACTIVITY IS HEAVY-TAILED</text>')
    body, tail, ridge, mx, my = density_paths(dx0, dx1, dbase, dh, pct)
    A(f'<path d="{body}" fill="{CURVE}"/>')
    A(f'<path d="{tail}" fill="{TAIL}" fill-opacity="0.9"/>')
    A(f'<path d="{ridge}" fill="none" stroke="{RIDGE}" stroke-width="1.4"/>')
    A(f'<line x1="{mx:.1f}" y1="{my:.1f}" x2="{mx:.1f}" y2="{dbase}" stroke="{INK}" stroke-width="1.5"/>')
    A(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="3.4" fill="{INK}">'
      f'<animate attributeName="r" values="3.4;4.6;3.4" dur="2.4s" repeatCount="indefinite"/>'
      f'<animate attributeName="fill-opacity" values="1;.55;1" dur="2.4s" repeatCount="indefinite"/></circle>')
    A(f'<text x="{mx-6:.1f}" y="{my-8:.1f}" fill="{INK}" font-size="10.5" text-anchor="end">you</text>')
    A(f'<line x1="{dx0}" y1="{dbase}" x2="{dx1}" y2="{dbase}" stroke="{HAIR}"/>')
    A(f'<text x="{dx0}" y="{dbase+14}" fill="{DIM}" font-size="9.5">fewer</text>')
    A(f'<text x="{dx1}" y="{dbase+14}" fill="{DIM}" font-size="9.5" text-anchor="end">more contributions</text>')

    # ---- right: ledger ----------------------------------------------------
    lx, lxr = 392, W - P
    A(f'<line x1="366" y1="64" x2="366" y2="232" stroke="{HAIR}"/>')
    A(f'<text x="{lx}" y="76" class="k">THIS YEAR · LAST 12 MONTHS</text>')
    rows = [("commits", commas(commits), INK),
            ("pull requests", commas(prs), INK),
            ("issues", commas(issues), INK),
            ("longest streak", f"{longest} days", INK),
            ("current streak", f"{cur} days", GREEN if cur else DIM),
            ("total contributions", commas(total), INK)]
    ry = 104
    for lab, val, ac in rows:
        A(f'<text x="{lx}" y="{ry}" class="lab">{lab}</text>')
        A(f'<text x="{lxr}" y="{ry}" class="m" fill="{ac}" font-size="14.5" '
          f'text-anchor="end">{val}</text>')
        A(f'<line x1="{lx}" y1="{ry+8}" x2="{lxr}" y2="{ry+8}" stroke="{HAIR}" stroke-opacity="0.5"/>')
        ry += 23

    # ---- languages band ---------------------------------------------------
    A(f'<line x1="{P}" y1="252" x2="{W-P}" y2="252" stroke="{HAIR}"/>')
    A(f'<text x="{P}" y="273" class="k">LANGUAGES</text>')
    bx, bw = 120, W - P - 120
    x = bx
    for name, p in langs:                          # stacked spectrum, 2px surface gaps
        seg = bw * p / 100
        A(f'<rect x="{x:.1f}" y="266" width="{max(2, seg-2):.1f}" height="9" rx="2.5" fill="{lc[name]}"/>')
        x += seg
    # legend
    gx = P
    A_gy = 292
    for name, p in langs:
        A(f'<circle cx="{gx+4}" cy="{A_gy-4}" r="3.6" fill="{lc[name]}"/>')
        t = f"{esc(name)} {p:.0f}%"
        A(f'<text x="{gx+13}" y="{A_gy}" fill="{TXT}" font-size="11.5">{t}</text>')
        gx += 13 + len(t) * 6.6 + 18
    A(f'<text x="{W-P}" y="{A_gy}" fill="{DIM}" font-size="10.5" text-anchor="end">'
      f'updated {time.strftime("%b %-d, %Y", time.gmtime())}</text>')

    A('</svg>')
    return "\n".join(s)


if __name__ == "__main__":
    svg = build()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes)")
