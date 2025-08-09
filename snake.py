#!/usr/bin/env python3
import os
import requests
from xml.sax.saxutils import escape
from datetime import datetime

# === Konfiguracja ===
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
USERNAME = os.environ.get("GH_USER") or os.environ.get("GITHUB_ACTOR") or ""

if not GH_TOKEN:
    raise SystemExit("Brak GH_TOKEN lub GITHUB_TOKEN w środowisku!")
if not USERNAME:
    raise SystemExit("Brak GH_USER (nazwa użytkownika)!")

# Pobranie danych z GitHub GraphQL API
query = """
query($userName:String!) {
  user(login: $userName) {
    contributionsCollection {
      contributionCalendar {
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

# === Ustawienia SVG ===
cell = 14
gap = 2
cols = len(weeks)
rows = max(len(w["contributionDays"]) for w in weeks)
width = cols * (cell + gap) + 20
height = rows * (cell + gap) + 40
margin = 10

# Punkty z kontrybucjami
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
    with open("snake.svg", "w", encoding="utf-8") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="20">Brak kontrybucji</text></svg>')
    raise SystemExit("Brak kontrybucji.")

# Ścieżka dla węża
path_cmds = [("M" if i == 0 else "L") + f"{cx:.2f},{cy:.2f}" for i, (cx, cy, *_rest) in enumerate(points)]
path_str = " ".join(path_cmds)

# Parametry animacji
step = 0.45
total_dur = max(2.0, len(points) * step)
head_r = cell * 0.45

# Ile sekund wcześniej wąż "zjada" pole (efekt klasycznego snake)
lead_time = 0.9  # można dostosować

# === Tworzenie SVG ===
svg_parts = []
svg_parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'xmlns:xlink="http://www.w3.org/1999/xlink" '
    f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
)

# Style z trybem ciemnym
svg_parts.append('''
<style>
@media (prefers-color-scheme: dark) {
  .bg { fill: url(#bgGradientDark); }
  .cell { stroke: #374151; }
  .label { fill: #f3f4f6; }
}
@media (prefers-color-scheme: light) {
  .bg { fill: url(#bgGradientLight); }
  .cell { stroke: #d1d5db; }
  .label { fill: #1f2937; }
}
</style>
''')

# Definicje gradientów i cieni
svg_parts.append(f'''
<defs>
  <linearGradient id="bgGradientLight" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#f8fafc"/>
    <stop offset="100%" stop-color="#e2e8f0"/>
  </linearGradient>
  <linearGradient id="bgGradientDark" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#1f2937"/>
    <stop offset="100%" stop-color="#111827"/>
  </linearGradient>
  <linearGradient id="snakeGradient" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#34d399"/>
    <stop offset="100%" stop-color="#059669"/>
  </linearGradient>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="2" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.3"/>
  </filter>
</defs>
''')

# Tło
svg_parts.append(f'<rect class="bg" width="100%" height="100%" filter="url(#shadow)"/>')

# Kwadraty kontrybucji
for r in rects:
    title = escape(f"{r['date']} — {r['count']} contributions")
    svg_parts.append(f'<g>')
    svg_parts.append(f'<rect id="{r["id"]}" x="{r["x"]}" y="{r["y"]}" width="{r["w"]}" height="{r["h"]}" rx="2" ry="2" fill="{r["fill"]}" class="cell" />')
    svg_parts.append(f'<title>{title}</title>')
    svg_parts.append(f'</g>')

# Ścieżka ruchu węża
svg_parts.append(f'<path id="snakePath" d="{escape(path_str)}" fill="none" stroke="none" />')

# Wąż z ogonem
svg_parts.append(f'<g id="snake">')
# Głowa
svg_parts.append(f'  <circle id="head" r="{head_r}" cx="0" cy="0" fill="url(#snakeGradient)" stroke="#065f46" stroke-width="1"/>')
svg_parts.append(f'''  <animateMotion xlink:href="#head" dur="{total_dur}s" repeatCount="indefinite">
    <mpath xlink:href="#snakePath" />
  </animateMotion>''')
# Ogon
for i in range(1, 5):
    delay = i * 0.2
    size = max(2, head_r - i*2)
    svg_parts.append(f'''
    <circle r="{size}" fill="url(#snakeGradient)" opacity="{1 - i*0.2}">
      <animateMotion dur="{total_dur}s" repeatCount="indefinite" begin="{delay}s">
        <mpath xlink:href="#snakePath" />
      </animateMotion>
    </circle>
    ''')
svg_parts.append('</g>')

# Efekt błysku przy jedzeniu z wyprzedzeniem
for i, (_, _, date, cnt, color, rect_id) in enumerate(points):
    begin = max(0, i * step - lead_time)  # animacja zaczyna się wcześniej niż ruch węża
    svg_parts.append(f'<animate xlink:href="#{rect_id}" attributeName="fill-opacity" from="1" to="0.1" begin="{begin:.2f}s" dur="0.15s" fill="freeze" />')
    cx = rects[int(rect_id[1:])]["x"] + cell/2
    cy = rects[int(rect_id[1:])]["y"] + cell/2
    svg_parts.append(f'''
    <circle cx="{cx}" cy="{cy}" r="0" fill="#facc15" opacity="0.8">
      <animate attributeName="r" begin="{begin:.2f}s" dur="0.3s" values="0;8;0" fill="freeze" />
      <animate attributeName="opacity" begin="{begin:.2f}s" dur="0.3s" values="0.8;0;0" fill="freeze" />
    </circle>
    ''')

# Podpis
svg_parts.append(f'<text x="{margin}" y="{height-10}" class="label" font-family="sans-serif" font-size="12">Generated {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")} — snake eats your contributions</text>')

svg_parts.append('</svg>')

# Zapis
with open("snake.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(svg_parts))

print("✅ Wygenerowano snake.svg z efektem zjadania z wyprzedzeniem")
