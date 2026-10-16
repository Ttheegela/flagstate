"""Build the SVG; use --png to also export at 2x resolution (requires PyMuPDF)."""
from html import escape
from pathlib import Path
import re
import sys

OUT = Path(__file__).parent
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1280" viewBox="0 0 1600 1280" role="img" aria-labelledby="title desc">
<title id="title">Flagstate — Agent System Design</title>
<desc id="desc">Static Vercel frontend and FastAPI service, evidence intake, the sequential lookup, recall, browse, analyse, remember, brief and evaluation pipeline, and cited results with optional audio.</desc>
<defs>''']
colors = {"blue": "#3275e9", "teal": "#00a497", "green": "#15945b", "orange": "#e48a07", "red": "#dc5639"}
for key, value in colors.items():
    parts.append(f'<marker id="{key}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0L8 4L0 8Z" fill="{value}"/></marker>')
parts.append('''</defs><style>
text{font-family:Segoe UI,Arial,sans-serif;fill:#193652}
.title{font-size:36px;font-weight:750}.sub{font-size:17px;fill:#6c7e94}
.heading{font-size:23px;font-weight:700}.cardtitle{font-size:19px;font-weight:700}
.body{font-size:16px;fill:#576d83}.small{font-size:14px;fill:#6c7e94}
.tag{font-size:13px;font-weight:700;letter-spacing:1.7px}
</style><rect width="1600" height="1280" fill="#f7f9fc"/>''')


def text(x, y, value, cls="body", fill=None):
    sizes = {"title": 36, "sub": 17, "heading": 23, "cardtitle": 19, "body": 16, "small": 14, "tag": 13}
    weight = 700 if cls in {"title", "heading", "cardtitle", "tag"} else 400
    color = fill or ("#6c7e94" if cls in {"small", "sub"} else "#576d83" if cls == "body" else "#193652")
    parts.append(f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{sizes[cls]}" font-weight="{weight}" fill="{color}">{escape(value)}</text>')


def rect(x, y, w, h, fill="white", stroke="#c8d5e6", rx=12):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')


def card(x, y, w, h, title, lines, color="blue", fill="white", label=None):
    rect(x, y, w, h, fill)
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="5" rx="2.5" fill="{colors[color]}"/>')
    ty = y + 32
    if label:
        text(x + 18, y + 28, label, "tag", colors[color])
        ty = y + 57
    text(x + 18, ty, title, "cardtitle")
    for i, line in enumerate(lines):
        text(x + 18, ty + 27 + i * 23, line)


def arrow(d, color="blue", dashed=False):
    parts.append(f'<path d="{d}" fill="none" stroke="{colors[color]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"' + (' stroke-dasharray="6 5"' if dashed else '') + '/>')
    coords = re.findall(r"[MHV]|-?\d+", d)
    x, y = float(coords[1]), float(coords[2])
    i = 3
    dx, dy = 1, 0
    while i < len(coords):
        cmd, n = coords[i], float(coords[i + 1])
        if cmd == "H":
            dx, dy, x = (1 if n > x else -1), 0, n
        else:
            dx, dy, y = 0, (1 if n > y else -1), n
        i += 2
    pts = [(x,y), (x-9*dx+4*dy,y-9*dy-4*dx), (x-9*dx-4*dy,y-9*dy+4*dx)]
    parts.append(f'<polygon points="{" ".join(f"{a},{b}" for a,b in pts)}" fill="{colors[color]}"/>')


def band(y, title, subtitle, color, fill):
    rect(60, y, 1480, 66, fill, colors[color])
    parts.append(f'<rect x="69" y="{y+11}" width="6" height="44" rx="3" fill="{colors[color]}"/>')
    text(90, y + 29, title, "heading")
    text(90, y + 51, subtitle, "small")


text(60, 58, "Flagstate — Agent System Design", "title")
text(60, 88, "How a name, IMO number or recording becomes a sourced sanctions investigation", "sub")
text(1322, 55, "SOFTWARE ARCHITECTURE", "tag", colors["blue"])
text(1390, 81, "October 2026", "small")

# Entry points and runtime. Voice calls the service directly, alongside the site.
card(60, 132, 230, 117, "User / Analyst", ["Ship, company or person", "Text, voice or recording"], fill="#edf3ff")
card(330, 132, 270, 117, "Static Frontend", ["HTML + CSS + JavaScript", "Vercel · search + dossiers"], fill="#edf3ff")
card(650, 132, 280, 117, "FastAPI Service", ["Python · in-memory jobs", "One worker thread per job"], fill="#edf3ff")
card(980, 132, 250, 117, "Pipeline Runner", ["Seven ordered steps", "Step status + elapsed time"], fill="#edf3ff")
card(1280, 132, 260, 117, "Voice Agent", ["ElevenLabs Conversational AI", "/tools/search · investigate", "/tools/status"], fill="#edf3ff")
arrow("M290 190H330")
arrow("M600 190H650")
arrow("M930 190H980")
arrow("M1410 132V113H790V132")
text(858, 107, "Voice webhooks", "small")
text(654, 274, "POST /investigate → job_id     ·     GET /jobs/{id} → progress + result", "small")

rect(60, 296, 1480, 48)
text(81, 326, "Design principle:", "cardtitle")
text(250, 326, "Python detects changes and risk; the LLM writes from gathered evidence; every briefing claim carries a source.")

band(370, "Layer 1 · Evidence and Intake", "Separate access paths for quick dossiers, live investigation inputs and recorded speech", "teal", "#e7f6f3")
card(90, 457, 450, 145, "Research + Official Lists", ["Research snapshot + US / UK / EU / UN", "data/research-index.json + data/lists/*.json", "Used by browser search and pipeline lookup"], "teal")
card(575, 457, 450, 145, "Wider Search + Connections", ["OpenSanctions + US lobbying filings", "Vercel /api/search + /api/connections", "Cached assets from GitHub data-latest release"], "teal")
card(1060, 457, 450, 145, "Recording / Transcript", ["ElevenLabs Scribe · speakers + timestamps", "POST /scribe or /scribe/text", "Match aliases + valid IMOs → select an entity"], "teal")
text(580, 626, "Dossier enrichment in the frontend", "small", colors["teal"])
arrow("M220 602V670", "teal")
text(232, 647, "Local lookup inputs", "small", colors["teal"])
arrow("M1285 602V652H330V670", "teal", True)
text(1094, 644, "User starts investigation", "small", colors["teal"])

band(670, "Layer 2 · Live Investigation", "Sequential execution · each step records done, skipped or error and continues with available context", "green", "#eaf6ee")
xs = [90, 380, 670, 960, 1250]
steps = [
    ("Lookup", ["Resolve name / IMO", "Research + list matches", "lookup.py"]),
    ("Recall", ["SurrealDB Agent Memory", "Previous facts + history", "memory.py"]),
    ("Browse", ["Anchor Browser", "VesselFinder / OpenCorporates", "browse.py"]),
    ("Analyse", ["Daytona sandbox · Python", "Risk flags + change detection", "sandbox.py / analysis.py"]),
    ("Remember", ["SurrealDB Agent Memory", "New facts supersede old ones", "memory.py"]),
]
for i, (x, (title, lines)) in enumerate(zip(xs, steps)):
    card(x, 758, 260, 150, title, lines, "green", label=f"0{i+1}")
    if i < 4:
        arrow(f"M{x+260} 833H{xs[i+1]}", "green")
# Context flows from the last investigation step into synthesis.
arrow("M1380 908V938H220V960", "orange")
rect(595, 921, 410, 32, "#f7f9fc", "#f7f9fc", 3)
text(614, 943, "Gathered context + risk flags + change history", "small", colors["orange"])

band(960, "Layer 3 · Briefing, Evaluation and Delivery", "Synthesize the evidence, measure citation coverage and return a readable or spoken result", "orange", "#fff5e6")
arrow("M245 1026V1048", "orange")
card(90, 1048, 310, 143, "Brief", ["AWS Bedrock · Claude Haiku 4.5", "Gathered context only", "Short briefing + cited claims"], "orange", label="06")
card(450, 1048, 310, 143, "Evaluate", ["Claim source URLs vs. context", "Grounding score logged to Arize", "Measures coverage, not truth"], "red", label="07")
card(810, 1048, 310, 143, "Investigation Result", ["Briefing + numbered sources", "Risk flags + change timeline", "Returned through job polling"], "blue", fill="#edf3ff")
card(1170, 1048, 340, 143, "Spoken Briefing", ["ElevenLabs text-to-speech", "GET /jobs/{id}/audio", "Optional playback from the result"], "orange")
arrow("M400 1120H450", "orange")
arrow("M760 1120H810", "blue")
arrow("M1120 1120H1170", "orange", True)

text(60, 1223, "Observability:", "cardtitle")
text(201, 1223, "Arize AX traces the full investigation: agent, tool, LLM and evaluator spans.")
text(60, 1253, "Fallbacks: local JSON memory · local Python analysis · template briefing. Agent hosting is configured separately from Vercel.", "small")
parts.append('</svg>')
(OUT / "Software Architecture.svg").write_text("\n".join(parts), encoding="utf-8")
print(OUT / "Software Architecture.svg")
if "--png" in sys.argv:
    import fitz

    with fitz.open(OUT / "Software Architecture.svg") as document:
        document[0].get_pixmap(matrix=fitz.Matrix(2, 2)).save(OUT / "Software Architecture.png")
    print(OUT / "Software Architecture.png")
