#!/usr/bin/env python3
"""Generate a self-hosted GitHub "scorecard" as a static SVG.

Runs in CI with the built-in GITHUB_TOKEN, writes an SVG committed to the
`output` branch, so the profile README never depends on a live third-party
stats server at render time. Public data only.

The rank is github-readme-stats' own published algorithm (calculateRank),
re-implemented faithfully — an honest, reproducible grade, not a hand-tuned one.
Palette matches bjorkslefteyelash.com/api/nowplaying.svg (tokyonight).
"""
import json
import os
import sys
import time
import urllib.request

LOGIN = os.environ.get("STATS_LOGIN", "cupidthatbtc")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist/github-stats-dark.svg"

# ---- palette (exact now-playing card colours) -----------------------------
BG = "#1a1b27"
HAIR = "#292e42"
INK = "#c0caf5"
TXT = "#a9b1d6"
DIM = "#565f89"
BLUE = "#7aa2f7"          # scorecard accent (data side)
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
      totalPullRequestReviewContributions
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


def calculate_rank(commits, prs, issues, reviews, stars, followers):
    """Faithful re-implementation of anuraghazra/github-readme-stats
    src/calculateRank.js (all_commits = false)."""
    def exp_cdf(x):
        return 1 - 2 ** (-x)

    def logn_cdf(x):
        return x / (1 + x)

    terms = [
        (2, exp_cdf(commits / 250)),
        (3, exp_cdf(prs / 50)),
        (1, exp_cdf(issues / 25)),
        (1, exp_cdf(reviews / 2)),
        (4, logn_cdf(stars / 50)),
        (1, logn_cdf(followers / 10)),
    ]
    total_w = sum(w for w, _ in terms)
    rank = 1 - sum(w * v for w, v in terms) / total_w
    pct = rank * 100
    thresholds = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    level = levels[next(i for i, t in enumerate(thresholds) if pct <= t)]
    return level, pct


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
    reviews = cc["totalPullRequestReviewContributions"]
    stars = sum(r["stargazerCount"] for r in repos)
    followers = u["followers"]["totalCount"]
    repo_n = u["repositories"]["totalCount"]
    total = cal["totalContributions"]
    cur, longest = streaks(days)
    letter, pct = calculate_rank(commits, prs, issues, reviews, stars, followers)

    lb, lc = {}, {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            lb[n] = lb.get(n, 0) + e["size"]
            lc[n] = e["node"]["color"] or "#8a8a8a"
    lt = sum(lb.values()) or 1
    langs = [(n, b / lt * 100) for n, b in sorted(lb.items(), key=lambda kv: -kv[1])
             if b / lt * 100 >= 0.5][:4]

    W, H, P = 820, 278, 30
    s = []
    A = s.append
    A(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
      f'role="img" aria-label="GitHub scorecard for {esc(u["login"])} — rank {letter}, top {round(pct)}%">')
    A(f'<style>text{{font-family:{SANS};}} .m{{font-family:{MONO};}} '
      f'.k{{fill:{DIM};font-size:9.5px;letter-spacing:2px;}} .lab{{fill:{TXT};font-size:12.5px;}}</style>')
    A(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="{BG}" stroke="{HAIR}"/>')

    # ---- masthead ---------------------------------------------------------
    A(f'<text x="{P}" y="35" fill="{INK}" font-size="16.5" font-weight="600">'
      f'{esc(u["login"])}<tspan fill="{DIM}" font-weight="400"> / scorecard</tspan></text>')
    A(f'<text x="{W-P}" y="34" class="k" text-anchor="end">'
      f'<tspan class="m" fill="{TXT}" letter-spacing="0">{followers}</tspan> FOLLOWERS'
      f'<tspan fill="{DIM}">  ·  </tspan><tspan class="m" fill="{TXT}" letter-spacing="0">{repo_n}</tspan> REPOS'
      f'<tspan fill="{DIM}">  ·  </tspan><tspan class="m" fill="{TXT}" letter-spacing="0">{stars}</tspan> STARS</text>')
    A(f'<line x1="{P}" y1="50" x2="{W-P}" y2="50" stroke="{HAIR}"/>')

    # ---- left: grade ------------------------------------------------------
    A(f'<text x="{P}" y="78" class="k">ACTIVITY RANK</text>')
    A(f'<text x="{P}" y="150" fill="{INK}" font-size="76" font-weight="800" '
      f'letter-spacing="-2">{letter}</text>')
    A(f'<rect x="{P+2}" y="160" width="52" height="3" rx="1.5" fill="{GREEN}"/>')
    gw = 46 if len(letter) == 1 else 82
    px0 = P + gw + 24
    A(f'<text x="{px0}" y="108" fill="{DIM}" font-size="12">top</text>')
    A(f'<text x="{px0}" y="140" class="m" fill="{INK}" font-size="30" font-weight="700">{round(pct)}%</text>')
    A(f'<text x="{px0}" y="158" fill="{DIM}" font-size="11">of contributors</text>')
    A(f'<text x="{P}" y="190" fill="{DIM}" font-size="10.5">via the '
      f'<tspan fill="{TXT}">github-readme-stats</tspan> rank formula</text>')

    # ---- right: ledger ----------------------------------------------------
    lx, lxr = 392, W - P
    A(f'<line x1="366" y1="64" x2="366" y2="214" stroke="{HAIR}"/>')
    A(f'<text x="{lx}" y="78" class="k">THIS YEAR · LAST 12 MONTHS</text>')
    rows = [("commits", commas(commits), INK), ("pull requests", commas(prs), INK),
            ("issues", commas(issues), INK), ("longest streak", f"{longest} days", INK),
            ("current streak", f"{cur} days", GREEN if cur else DIM),
            ("total contributions", commas(total), INK)]
    ry = 100
    for lab, val, ac in rows:
        A(f'<text x="{lx}" y="{ry}" class="lab">{lab}</text>')
        A(f'<text x="{lxr}" y="{ry}" class="m" fill="{ac}" font-size="14.5" text-anchor="end">{val}</text>')
        A(f'<line x1="{lx}" y1="{ry+8}" x2="{lxr}" y2="{ry+8}" stroke="{HAIR}" stroke-opacity="0.55"/>')
        ry += 20

    # ---- languages band ---------------------------------------------------
    A(f'<line x1="{P}" y1="226" x2="{W-P}" y2="226" stroke="{HAIR}"/>')
    A(f'<text x="{P}" y="246" class="k">LANGUAGES</text>')
    bx, bw = 122, W - P - 122
    x = bx
    for name, p in langs:
        seg = bw * p / 100
        A(f'<rect x="{x:.1f}" y="240" width="{max(2, seg-2):.1f}" height="8" rx="2" fill="{lc[name]}"/>')
        x += seg
    # legend row
    gx = P
    for name, p in langs:
        A(f'<circle cx="{gx+4}" cy="{266-4}" r="3.4" fill="{lc[name]}"/>')
        t = f"{esc(name)} {p:.0f}%"
        A(f'<text x="{gx+12}" y="266" fill="{TXT}" font-size="11.5">{t}</text>')
        gx += 12 + len(t) * 6.6 + 18
    A(f'<text x="{W-P}" y="266" fill="{DIM}" font-size="10.5" text-anchor="end">'
      f'updated {time.strftime("%b %-d, %Y", time.gmtime())}</text>')

    A('</svg>')
    return "\n".join(s)


if __name__ == "__main__":
    svg = build()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes)")
