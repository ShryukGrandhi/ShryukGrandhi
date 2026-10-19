"""Generate dark_mode.svg / light_mode.svg for the GitHub profile README.

Left side: spinning ASCII donut (pre-rendered frames, CSS-animated).
Right side: neofetch-style info + live GitHub stats.

Env: GH_TOKEN (or GITHUB_TOKEN) for the GraphQL API.
"""
import json
import math
import os
import urllib.request
from datetime import datetime, timezone

USER = "ShryukGrandhi"

# ---- edit these to change what the card says -------------------------------
INFO = [
    ("title", "shryuk@grandhi"),
    ("kv", "OS", "Windows 11, macOS, Ubuntu"),
    ("kv", "Uptime", "{uptime}"),
    ("kv", "Host", "builds agents, bots & weird demos"),
    ("kv", "Kernel", "hackathon-driven development"),
    ("kv", "IDE", "VSCode, Cursor, Claude Code"),
    ("blank",),
    ("kv", "Languages.Programming", "TypeScript, Python, Java"),
    ("kv", "Languages.Computer", "HTML, CSS, JSON, YAML, Luau"),
    ("kv", "Languages.Real", "English"),
    ("blank",),
    ("kv", "Hobbies.Software", "AI agents, automation, Roblox games"),
    ("kv", "Hobbies.Other", "trading bots, AI video"),
    ("blank",),
    ("section", "Contact"),
    ("kv", "GitHub", "ShryukGrandhi"),
    ("blank",),
    ("section", "GitHub Stats"),
    ("stats",),
]
# -----------------------------------------------------------------------------

WIDTH, HEIGHT = 985, 450
LEFT_X, RIGHT_X, TOP_Y, LINE_H = 15, 390, 30, 20
INFO_COLS = 58  # characters per right-side line (dot padding target)

COLS, ROWS, FRAMES, PERIOD = 40, 21, 60, 4.0
SHADES = ".,-~:;=!*#$@"

THEMES = {
    "dark": dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", val="#a5d6ff",
                 dots="#616e7f", add="#3fb950", dele="#f85149",
                 g1="#ff7b72", g2="#d2a8ff", g3="#79c0ff"),
    "light": dict(bg="#f6f8fa", fg="#24292f", key="#953800", val="#0a3069",
                  dots="#c2cfde", add="#1a7f37", dele="#cf222e",
                  g1="#cf222e", g2="#8250df", g3="#0969da"),
}


# ---- donut ------------------------------------------------------------------
def donut_frame(a, b):
    out = [" "] * (COLS * ROWS)
    zbuf = [0.0] * (COLS * ROWS)
    ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
    j = 0.0
    while j < 6.28:
        cj, sj = math.cos(j), math.sin(j)
        i = 0.0
        while i < 6.28:
            ci, si = math.cos(i), math.sin(i)
            h = cj + 2
            d = 1 / (si * h * sa + sj * ca + 5)
            t = si * h * ca - sj * sa
            x = int(COLS / 2 + COLS * 0.62 * d * (ci * h * cb - t * sb))
            y = int(ROWS / 2 + ROWS * 0.52 * d * (ci * h * sb + t * cb))
            n = int(8 * ((sj * sa - si * cj * ca) * cb - si * cj * sa - sj * ca - ci * cj * sb))
            o = x + COLS * y
            if 0 <= y < ROWS and 0 <= x < COLS and d > zbuf[o]:
                zbuf[o] = d
                out[o] = SHADES[max(n, 0)]
            i += 0.02
        j += 0.07
    return ["".join(out[r * COLS:(r + 1) * COLS]) for r in range(ROWS)]


def donut_svg():
    step = PERIOD / FRAMES
    groups = []
    for f in range(FRAMES):
        # a, b advance by a full turn of their combined motion over the loop
        a = 2 * math.pi * f / FRAMES
        b = 4 * math.pi * f / FRAMES
        lines = donut_frame(a, b)
        tspans = "".join(
            f'<tspan x="{LEFT_X}" y="{TOP_Y + r * LINE_H}">{line}</tspan>'
            for r, line in enumerate(lines))
        delay = -(FRAMES - f) * step
        groups.append(f'<text class="d" style="animation-delay:{delay:.3f}s">{tspans}</text>')
    pct = 100 / FRAMES
    css = (f".d{{opacity:0;animation:spin {PERIOD}s steps(1,end) infinite;fill:url(#g)}}"
           f"@keyframes spin{{0%{{opacity:1}}{pct:.4f}%{{opacity:0}}100%{{opacity:0}}}}")
    return css, "\n".join(groups)


# ---- github stats -----------------------------------------------------------
def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": USER})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats(token):
    base = gql("""query($u:String!){user(login:$u){id createdAt followers{totalCount}
      repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){totalCount}}}""",
               {"u": USER}, token)["user"]
    repos, cursor = [], None
    while True:
        page = gql("""query($u:String!,$c:String){user(login:$u){repositories(first:100,after:$c,
          ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC){pageInfo{hasNextPage endCursor}
          nodes{name stargazerCount defaultBranchRef{name}}}}}""",
                   {"u": USER, "c": cursor}, token)["user"]["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    commits = adds = dels = 0
    for repo in repos:
        if not repo["defaultBranchRef"]:
            continue
        cursor = None
        while True:
            hist = gql("""query($o:String!,$n:String!,$id:ID!,$c:String){repository(owner:$o,name:$n){
              defaultBranchRef{target{...on Commit{history(first:100,after:$c,author:{id:$id}){
              totalCount pageInfo{hasNextPage endCursor} nodes{additions deletions}}}}}}}""",
                       {"o": USER, "n": repo["name"], "id": base["id"], "c": cursor},
                       token)["repository"]["defaultBranchRef"]["target"]["history"]
            if cursor is None:
                commits += hist["totalCount"]
            for c in hist["nodes"]:
                adds += c["additions"]
                dels += c["deletions"]
            if not hist["pageInfo"]["hasNextPage"]:
                break
            cursor = hist["pageInfo"]["endCursor"]

    return dict(
        created=base["createdAt"],
        repos=len(repos),
        contributed=base["repositoriesContributedTo"]["totalCount"],
        stars=sum(r["stargazerCount"] for r in repos),
        followers=base["followers"]["totalCount"],
        commits=commits, adds=adds, dels=dels)


def uptime(created_iso):
    start = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    months = (now.year - start.year) * 12 + now.month - start.month
    if now.day < start.day:
        months -= 1
    anchor_m = start.month + months
    anchor = start.replace(year=start.year + (anchor_m - 1) // 12, month=(anchor_m - 1) % 12 + 1)
    days = (now - anchor).days
    y, m = divmod(months, 12)
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(days, 'day')}"


# ---- info panel ---------------------------------------------------------------
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def kv_line(key, val, width=INFO_COLS):
    dots = width - len(key) - len(val) - 6  # ". " + ": " + 2 spaces
    dots = max(dots, 1)
    return (f'<tspan class="c">. </tspan><tspan class="k">{esc(key)}</tspan>:'
            f'<tspan class="c"> {"." * dots} </tspan><tspan class="v">{esc(val)}</tspan>')


def fmt(n):
    return f"{n:,}"


def info_svg(stats):
    rows = []
    for item in INFO:
        kind = item[0]
        if kind == "title":
            rows.append(f'{esc(item[1])} <tspan class="c">{"—" * (INFO_COLS - len(item[1]) - 1)}</tspan>')
        elif kind == "section":
            rows.append(f'<tspan class="c">- </tspan>{esc(item[1])} '
                        f'<tspan class="c">{"—" * (INFO_COLS - len(item[1]) - 3)}</tspan>')
        elif kind == "blank":
            rows.append('<tspan class="c">.</tspan>')
        elif kind == "kv":
            rows.append(kv_line(item[1], item[2].format(uptime=uptime(stats["created"]))))
        elif kind == "stats":
            half = 30
            rows.append(kv_line("Repos", f'{stats["repos"]} {{Contributed: {stats["contributed"]}}}', half)
                        + ' | ' + kv_line("Stars", fmt(stats["stars"]), INFO_COLS - half - 3)[len('<tspan class="c">. </tspan>'):])
            rows.append(kv_line("Commits", fmt(stats["commits"]), half)
                        + ' | ' + kv_line("Followers", fmt(stats["followers"]), INFO_COLS - half - 3)[len('<tspan class="c">. </tspan>'):])
            loc = stats["adds"] - stats["dels"]
            tail = f'{fmt(loc)} ( {fmt(stats["adds"])}++, {fmt(stats["dels"])}-- )'
            dots = max(INFO_COLS - len("Lines of Code on GitHub") - len(tail) - 6, 1)
            rows.append(f'<tspan class="c">. </tspan><tspan class="k">Lines of Code on GitHub</tspan>:'
                        f'<tspan class="c"> {"." * dots} </tspan><tspan class="v">{fmt(loc)}</tspan> ( '
                        f'<tspan class="a">{fmt(stats["adds"])}++</tspan>, '
                        f'<tspan class="r">{fmt(stats["dels"])}--</tspan> )'
                        f'<tspan class="cur">█</tspan>')
    return "\n".join(f'<tspan x="{RIGHT_X}" y="{TOP_Y + i * LINE_H}">{r}</tspan>'
                     for i, r in enumerate(rows))


def build(theme, stats, donut_css, donut_body):
    t = THEMES[theme]
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,'Courier New',monospace" width="{WIDTH}px" height="{HEIGHT}px" font-size="16px">
<style>
@font-face{{src:local('Consolas'),local('Consolas Bold');font-family:'ConsolasFallback';font-display:swap;-webkit-size-adjust:109%;size-adjust:109%}}
text,tspan{{white-space:pre}}
.k{{fill:{t["key"]}}} .v{{fill:{t["val"]}}} .c{{fill:{t["dots"]}}} .a{{fill:{t["add"]}}} .r{{fill:{t["dele"]}}}
.cur{{fill:{t["fg"]};animation:blink 1.1s steps(1,end) infinite}}
@keyframes blink{{0%{{opacity:1}}50%{{opacity:0}}100%{{opacity:0}}}}
{donut_css}
</style>
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1" gradientUnits="objectBoundingBox">
<stop offset="0" stop-color="{t["g1"]}"><animate attributeName="stop-color" values="{t["g1"]};{t["g2"]};{t["g3"]};{t["g1"]}" dur="8s" repeatCount="indefinite"/></stop>
<stop offset="1" stop-color="{t["g3"]}"><animate attributeName="stop-color" values="{t["g3"]};{t["g1"]};{t["g2"]};{t["g3"]}" dur="8s" repeatCount="indefinite"/></stop>
</linearGradient></defs>
<rect width="{WIDTH}px" height="{HEIGHT}px" fill="{t["bg"]}" rx="15"/>
{donut_body}
<text x="{RIGHT_X}" y="{TOP_Y}" fill="{t["fg"]}">
{info_svg(stats)}
</text>
</svg>
'''


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("set GH_TOKEN or GITHUB_TOKEN")
    stats = fetch_stats(token)
    print(stats)
    css, body = donut_svg()
    for theme in THEMES:
        with open(f"{theme}_mode.svg", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(build(theme, stats, css, body))


if __name__ == "__main__":
    main()
