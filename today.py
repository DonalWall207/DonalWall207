"""
Builds dark_mode.svg and light_mode.svg for the GitHub profile README.
Runs daily through GitHub Actions (.github/workflows/build.yml).

Edit the CONFIG section to change what the card shows.
"""
import datetime
import os
import time
from xml.sax.saxutils import escape

import requests
from dateutil.relativedelta import relativedelta

import cards

# ───────────────────────────── CONFIG ─────────────────────────────
USER_NAME = os.environ.get("USER_NAME", "donalwall207")
BIRTHDAY = datetime.date(2002, 9, 8)  # <-- set your real birthday (year, month, day)

HEADER = "donal@wall"

# (key, value) pairs; key=None draws a section divider with value as its title
INFO = [
    ("OS", "Firmware Engineer @ IBM"),
    ("Uptime", "{uptime}"),
    ("Host", "MSc Computer Science"),
    ("Kernel", "Enterprise Software Systems"),
    ("IDE", "VS Code, IntelliJ, Android Studio"),
    (None, ""),
    ("Languages.Programming", "C, Python, Java, Kotlin, TS"),
    ("Languages.Computer", "HTML, CSS, SQL, Bash"),
    ("Tools", "Docker, Git, Linux, AWS, Azure"),
    ("Hobbies", "Football, F1, Rugby"),
    (None, ""),
    ("Previous", "SOC Analyst Intern @ State Street"),
    ("", "Bartender @ The Majestic Hotel"),
    (None, "Contact"),
    ("Email", "donaljohnwall@gmail.com"),
    ("LinkedIn", "donal-wall"),
    (None, "GitHub Stats"),
]

ASCII_ART = r"""
  ____                    _
 |  _ \  ___  _ __   __ _| |
 | | | |/ _ \| '_ \ / _` | |
 | |_| | (_) | | | | (_| | |
 |____/ \___/|_| |_|\__,_|_|

 __        __    _ _
 \ \      / /_ _| | |
  \ \ /\ / / _` | | |
   \ V  V / (_| | | |
    \_/\_/ \__,_|_|_|

  .------------------------.
  | $ make flash           |
  | [########----] 67%     |
  | target: ibm-firmware   |
  '------------------------'
"""

THEMES = {
    "dark_mode.svg": dict(bg="#161b22", text="#c9d1d9", key="#ffa657",
                          value="#a5d6ff", dots="#616e7f", add="#3fb950", dele="#f85149"),
    "light_mode.svg": dict(bg="#f6f8fa", text="#24292f", key="#953800",
                           value="#0a3069", dots="#c2cfde", add="#1a7f37", dele="#cf222e"),
}

WIDTH = 58          # characters per info line (key + dots + value)
LINE_H = 20         # px between lines
INFO_X = 390        # px where the info column starts
# ──────────────────────────────────────────────────────────────────

TOKEN = os.environ.get("ACCESS_TOKEN")
HEADERS = {"Authorization": f"bearer {TOKEN}"} if TOKEN else {}


def uptime():
    d = relativedelta(datetime.date.today(), BIRTHDAY)
    s = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{s(d.years, 'year')}, {s(d.months, 'month')}, {s(d.days, 'day')}"


def gql(query, variables):
    r = requests.post("https://api.github.com/graphql",
                      json={"query": query, "variables": variables},
                      headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


REPO_QUERY = """
query($login: String!, $cursor: String, $aff: [RepositoryAffiliation]) {
  user(login: $login) {
    id
    createdAt
    followers { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
    repositories(first: 100, after: $cursor, ownerAffiliations: $aff) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        nameWithOwner stargazerCount isFork
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}"""


def all_repos(aff):
    cursor, nodes, user = None, [], None
    while True:
        user = gql(REPO_QUERY, {"login": USER_NAME, "cursor": cursor, "aff": aff})["user"]
        page = user["repositories"]
        nodes += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return user, page["totalCount"], nodes
        cursor = page["pageInfo"]["endCursor"]


def repo_loc(name_with_owner):
    """Your additions, deletions and commits in one repo (all time)."""
    url = f"https://api.github.com/repos/{name_with_owner}/stats/contributors"
    for _ in range(8):
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 202:   # GitHub is still computing; wait and retry
            time.sleep(3)
            continue
        if r.status_code != 200 or not r.text:
            return 0, 0, 0
        for c in r.json() or []:
            if c.get("author") and c["author"]["login"].lower() == USER_NAME.lower():
                a = sum(w["a"] for w in c["weeks"])
                d = sum(w["d"] for w in c["weeks"])
                return a, d, c["total"]
        return 0, 0, 0
    return 0, 0, 0


def fetch_stats():
    if not TOKEN:
        return dict(repos="—", contrib="—", stars="—", commits="—",
                    followers="—", loc="—", add="—", dele="—",
                    _raw=dict(repos=0, contrib=0, stars=0, commits=0, followers=0,
                              loc=0, add=0, dele=0, years=0), _langs=[])
    user, repo_count, owned = all_repos(["OWNER"])
    _, _, every = all_repos(["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"])
    add = dele = commits = 0
    for repo in every:
        a, d, c = repo_loc(repo["nameWithOwner"])
        add, dele, commits = add + a, dele + d, commits + c

    # Top languages across your own (non-fork) repos, by bytes of code
    langs = {}
    for repo in owned:
        if repo["isFork"]:
            continue
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            size, color = langs.get(name, (0, e["node"]["color"] or "#8b949e"))
            langs[name] = (size + e["size"], color)
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:8]
    total = sum(v[0] for _, v in top) or 1
    top_langs = [(n, c, 100 * sz / total) for n, (sz, c) in top]

    created = datetime.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")).date()
    raw = dict(
        repos=repo_count,
        contrib=user["repositoriesContributedTo"]["totalCount"],
        stars=sum(r["stargazerCount"] for r in owned),
        commits=commits,
        followers=user["followers"]["totalCount"],
        loc=add - dele, add=add, dele=dele,
        years=relativedelta(datetime.date.today(), created).years,
    )
    fmt = {k: f"{v:,}" for k, v in raw.items() if k != "years"}
    return dict(**fmt, _raw=raw, _langs=top_langs)


# ─────────────────────────── SVG building ──────────────────────────
def t(s, cls=None):
    s = escape(s)
    return f'<tspan class="{cls}">{s}</tspan>' if cls else s


def kv_line(key, value):
    """'. Key:.......... value' padded to WIDTH characters."""
    if key == "":
        lead = "  "
        dots = " " * (WIDTH - len(lead) - len(value) - 1)
        return t(lead) + t(dots + " ", "dots") + t(value, "value")
    head = f". {key}:"
    n = max(1, WIDTH - len(head) - len(value) - 2)
    return (t(". ", "dots") + t(key, "key") + t(":") +
            t(" " + "." * n + " ", "dots") + t(value, "value"))


def divider(title):
    if not title:
        return t("—" * WIDTH, "dots")
    left = f"- {title} "
    return t("- ") + t(title, "key") + t(" " + "—" * (WIDTH - len(left) - 1), "dots")


def stat_pair(k1, v1, k2, v2):
    """Two stats on one line, e.g. Repos ... 12 | Stars ... 40"""
    half = (WIDTH - 3) // 2
    def part(k, v):
        n = max(1, half - len(f". {k}:") - len(v) - 2)
        return (t(". ", "dots") + t(k, "key") + t(":") +
                t(" " + "." * n + " ", "dots") + t(v, "value"))
    return part(k1, v1) + t(" | ") + part(k2, v2)


def build_lines(stats):
    lines = [t(HEADER) + t(" " + "—" * (WIDTH - len(HEADER) - 1), "dots")]
    for key, value in INFO:
        if key is None:
            lines.append(divider(value))
        else:
            lines.append(kv_line(key, value.format(uptime=uptime())))
    lines.append(stat_pair("Repos", f"{stats['repos']} {{Contributed: {stats['contrib']}}}",
                           "Stars", stats["stars"]))
    lines.append(stat_pair("Commits", stats["commits"], "Followers", stats["followers"]))
    loc_head = ". Lines of Code on GitHub:"
    loc_tail = f"{stats['loc']} ( {stats['add']}++, {stats['dele']}-- )"
    n = max(1, WIDTH - len(loc_head) - len(loc_tail) - 2)
    lines.append(t(". ", "dots") + t("Lines of Code on GitHub", "key") + t(":") +
                 t(" " + "." * n + " ", "dots") + t(stats["loc"], "value") +
                 t(" ( ") + t(stats["add"] + "++", "add") + t(", ") +
                 t(stats["dele"] + "--", "del") + t(" )"))
    return lines


def render(theme, stats):
    art = ASCII_ART.strip("\n").split("\n")
    info = build_lines(stats)
    rows = max(len(art), len(info))
    height = 30 + rows * LINE_H + 10
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="985" height="{height}" '
        f'font-family="ConsolasFallback, Consolas, \'Courier New\', monospace" font-size="16px">',
        "<style>",
        "@font-face { src: local('Consolas'), local('Consolas Bold'); font-family: 'ConsolasFallback';"
        " font-display: swap; -webkit-size-adjust: 109%; size-adjust: 109%; }",
        f".key {{fill: {theme['key']};}} .value {{fill: {theme['value']};}} "
        f".dots {{fill: {theme['dots']};}} .add {{fill: {theme['add']};}} .del {{fill: {theme['dele']};}}",
        "text, tspan {white-space: pre;}",
        "</style>",
        f'<rect width="985" height="{height}" fill="{theme["bg"]}" rx="15"/>',
        f'<text x="15" y="30" fill="{theme["text"]}" class="ascii" xml:space="preserve">',
    ]
    for i, line in enumerate(art):
        out.append(f'<tspan x="15" y="{30 + i * LINE_H}">{escape(line)}</tspan>')
    out.append("</text>")
    out.append(f'<text x="{INFO_X}" y="30" fill="{theme["text"]}" xml:space="preserve">')
    for i, line in enumerate(info):
        out.append(f'<tspan x="{INFO_X}" y="{30 + i * LINE_H}">{line}</tspan>')
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    stats = fetch_stats()
    print("Stats:", stats)
    for filename, theme in THEMES.items():
        with open(filename, "w", encoding="utf-8") as f:
            f.write(render(theme, stats))
        print("Wrote", filename)
    cards.write_all(THEMES, stats, "Donal's GitHub Stats")
