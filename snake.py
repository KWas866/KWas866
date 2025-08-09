#!/usr/bin/env python3

import os
import requests
import json
from xml.sax.saxutils import escape
from datetime import datetime

GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
if not GH_TOKEN:
    raise SystemExit(
        "Musisz ustawić zmienną środowiskową GH_TOKEN lub GITHUB_TOKEN.")

USERNAME = os.environ.get("GH_USER") or os.environ.get("GITHUB_ACTOR") or ""

query = """
query($userName:String!) {
  user(login: $userName) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

if not USERNAME:

    raise SystemExit(
        "Ustaw nazwę użytkownika w zmiennej GH_USER lub zapewnij GITHUB_ACTOR w środowisku Actions.")

headers = {"Authorization": f"Bearer {GH_TOKEN}"}
resp = requests.post(
    "https://api.github.com/graphql",
    json={"query": query, "variables": {"userName": USERNAME}},
    headers=headers,
    timeout=30,
)
resp.raise_for_status()
data = resp.json()
weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]


cell = 14
gap = 2
cols = len(weeks)
rows = max(len(w["contributionDays"]) for w in weeks)
width = cols * (cell + gap) + 20
height = rows * (cell + gap) + 20
margin = 10


points = []
rects = []
rect_id_seq = 0
for x, week in enumerate(weeks):
    for y, day in enumerate(week["contributionDays"]):
        cnt = day["contributionCount"]
        date = day["date"]
        color = day.get("color") or "#ebedf0"
        cx = margin + x * (cell + gap) + cell / 2
        cy = margin + y * (cell + gap) + cell / 2
        rect_id = f"r{rect_id_seq}"
        rect_id_seq += 1
        rects.append({
            "id": rect_id,
            "x": margin + x * (cell + gap),
            "y": margin + y * (cell + gap),
            "w": cell,
            "h": cell,
            "fill": color,
            "date": date,
            "count": cnt
        })
        if cnt and cnt > 0:
            points.append((cx, cy, date, cnt, color, rect_id))


if not points:
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="100%" height="100%" fill="white"/>
  <text x="{margin}" y="{margin+12}" font-family="sans-serif" font-size="12">Brak kontrybucji do animacji</text>
</svg>'''
    with open("snake.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("Wygenerowano snake.svg (brak punktów).")
    raise SystemExit(0)


path_cmds = []
for i, (cx, cy, *_rest) in enumerate(points):
    cmd = ("M" if i == 0 else "L") + f"{cx:.2f},{cy:.2f}"
    path_cmds.append(cmd)
path_str = " ".join(path_cmds)


step = 0.45
total_dur = max(2.0, len(points) * step)
head_r = cell * 0.45


svg_parts = []
svg_parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
svg_parts.append('<defs>')

svg_parts.append('''<style>
    .cell { stroke: #ddd; stroke-width: 1px; }
    .label { font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial; font-size:12px; fill:#333; }
</style>''')
svg_parts.append('</defs>')

svg_parts.append(f'<rect width="100%" height="100%" fill="white"/>')


for r in rects:

    title = escape(f"{r['date']} — {r['count']} contributions")
    svg_parts.append(f'<g>')
    svg_parts.append(
        f'<rect id="{r["id"]}" x="{r["x"]}" y="{r["y"]}" width="{r["w"]}" height="{r["h"]}" rx="2" ry="2" fill="{r["fill"]}" class="cell" />')
    svg_parts.append(f'<title>{title}</title>')
    svg_parts.append(f'</g>')


svg_parts.append(
    f'<path id="snakePath" d="{escape(path_str)}" fill="none" stroke="none" />')


svg_parts.append(f'<g id="snake">')
svg_parts.append(
    f'  <circle id="head" r="{head_r}" cx="0" cy="0" fill="#3b82f6" stroke="#0b63d6" stroke-width="1"/>')

svg_parts.append(f'''  <animateMotion xlink:href="#head" dur="{total_dur}s" repeatCount="indefinite">
    <mpath xlink:href="#snakePath" />
  </animateMotion>''')
svg_parts.append('</g>')

for i, (_, _, date, cnt, color, rect_id) in enumerate(points):
    begin = f"{i * step}s"

    svg_parts.append(
        f'<animate xlink:href="#{rect_id}" attributeName="fill-opacity" from="1" to="0.08" begin="{begin}" dur="0.12s" fill="freeze" />')

    cx_attr = 0
    crumb_id = f"c{i}"

    svg_parts.append(f'''
    <g transform="translate(0,0)">
      <circle id="{crumb_id}" cx="{0}" cy="{0}" r="{head_r*0.5}" fill="#ffb86b" opacity="0">
        <animate attributeName="opacity" begin="{begin}" dur="0.05s" from="0" to="1" fill="freeze" />
        <animateTransform attributeName="transform" type="translate" begin="{begin}" dur="0.9s" from="{0} {0}" to="5 -12" fill="freeze" />
        <animate attributeName="opacity" begin="{begin}" dur="0.9s" from="1" to="0" fill="freeze" />
      </circle>
      <title>{escape(date)} — {cnt} contributions</title>
    </g>
    ''')


svg_parts.append(
    f'<text x="{margin}" y="{height-6}" class="label">Generated on {datetime.utcnow().isoformat()}Z — snake eats your contributions</text>')

svg_parts.append('</svg>')

svg = "\n".join(svg_parts)

with open("snake.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Wygenerowano snake.svg")
