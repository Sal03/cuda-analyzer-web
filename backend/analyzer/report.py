from __future__ import annotations
import csv
import json
from dataclasses import asdict
from typing import List
from analyzer.models import SampleAnalysis


def write_json_report(path: str, analyses: List[SampleAnalysis]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(a) for a in analyses], f, indent=2)


def write_csv_report(path: str, analyses: List[SampleAnalysis]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sample_name", "total_score", "documentation",
                    "clarity", "best_practices", "modernity", "notes"])
        for a in analyses:
            w.writerow([
                a.sample_name,
                a.total_score,
                a.category_scores.get("Documentation", 0),
                a.category_scores.get("Clarity", 0),
                a.category_scores.get("Best Practices", 0),
                a.category_scores.get("Modernity", 0),
                " | ".join(a.summary),
            ])


def _grade(score: float) -> str:
    if score >= 85: return "A"
    if score >= 70: return "B"
    if score >= 55: return "C"
    if score >= 40: return "D"
    return "F"


def _color_class(score: float) -> str:
    if score >= 85: return "grade-a"
    if score >= 70: return "grade-b"
    if score >= 55: return "grade-c"
    return "grade-f"


def write_html_report(path: str, analyses: List[SampleAnalysis]) -> None:
    cats = ["Documentation", "Clarity", "Best Practices", "Modernity"]

    rows = ""
    cards = ""
    for a in analyses:
        grade = _grade(a.total_score)
        gc = _color_class(a.total_score)
        cat_cells = "".join(
            f'<td><span class="bar-wrap"><span class="bar" style="width:{a.category_scores.get(c,0)/a.category_max_scores.get(c,1)*100:.0f}%"></span></span>'
            f'<span class="bar-label">{a.category_scores.get(c,0):.1f}</span></td>'
            for c in cats
        )
        rows += f"""
        <tr>
          <td class="sample-name">{a.sample_name}</td>
          <td><span class="score-badge {gc}">{a.total_score:.0f} <sup class="grade">{grade}</sup></span></td>
          {cat_cells}
        </tr>"""

        # finding cards
        warnings = [r for r in a.rule_results if not r.passed]
        passes   = [r for r in a.rule_results if r.passed]
        w_items = "".join(f'<li class="finding fail"><span class="dot fail-dot"></span>{r.message}</li>' for r in warnings)
        p_items = "".join(f'<li class="finding pass"><span class="dot pass-dot"></span>{r.message}</li>' for r in passes)
        cards += f"""
        <div class="card">
          <div class="card-header">
            <span class="card-name">{a.sample_name}</span>
            <span class="score-badge {gc} card-score">{a.total_score:.0f}<sup class="grade">{grade}</sup></span>
          </div>
          <div class="card-cats">
            {"".join(f'<div class="cat-pill"><span class="cat-label">{c}</span><span class="cat-val">{a.category_scores.get(c,0):.0f}/{a.category_max_scores.get(c,1):.0f}</span></div>' for c in cats)}
          </div>
          <ul class="findings">{w_items}{p_items}</ul>
        </div>"""

    cat_headers = "".join(f"<th>{c}</th>" for c in cats)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CUDA Sample Quality Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

  :root {{
    --bg: #0d0d0d;
    --surface: #161616;
    --surface2: #1e1e1e;
    --border: #2a2a2a;
    --text: #e8e8e8;
    --muted: #888;
    --green: #39d353;
    --yellow: #e3b341;
    --orange: #f0883e;
    --red: #f85149;
    --blue: #58a6ff;
    --accent: #76e3c4;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'IBM Plex Sans', sans-serif; font-size: 14px; line-height: 1.6; }}

  header {{ border-bottom: 1px solid var(--border); padding: 32px 48px; display: flex; align-items: baseline; gap: 16px; }}
  .header-title {{ font-family: 'IBM Plex Mono', monospace; font-size: 22px; font-weight: 600; color: var(--accent); letter-spacing: -0.5px; }}
  .header-sub {{ color: var(--muted); font-size: 13px; }}

  main {{ padding: 40px 48px; max-width: 1400px; }}

  h2 {{ font-family: 'IBM Plex Mono', monospace; font-size: 13px; text-transform: uppercase; letter-spacing: 2px; color: var(--muted); margin-bottom: 20px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}

  /* TABLE */
  .table-wrap {{ overflow-x: auto; margin-bottom: 56px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--muted); text-align: left; padding: 10px 16px; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  td {{ padding: 12px 16px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: var(--surface2); }}

  .sample-name {{ font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: var(--blue); }}

  .score-badge {{ display: inline-flex; align-items: baseline; gap: 3px; font-family: 'IBM Plex Mono', monospace; font-size: 18px; font-weight: 600; padding: 2px 0; }}
  .grade {{ font-size: 10px; font-family: 'IBM Plex Sans', sans-serif; font-weight: 700; letter-spacing: 0.5px; opacity: 0.8; }}
  .grade-a {{ color: var(--green); }}
  .grade-b {{ color: var(--accent); }}
  .grade-c {{ color: var(--yellow); }}
  .grade-f {{ color: var(--red); }}

  .bar-wrap {{ display: inline-block; width: 60px; height: 4px; background: var(--surface2); border-radius: 2px; vertical-align: middle; margin-right: 6px; }}
  .bar {{ display: block; height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.3s; }}
  .bar-label {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--muted); }}

  /* CARDS */
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }}
  .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
  .card-name {{ font-family: 'IBM Plex Mono', monospace; font-size: 15px; font-weight: 600; color: var(--blue); }}
  .card-score {{ font-size: 22px; }}
  .card-cats {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }}
  .cat-pill {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; padding: 4px 10px; display: flex; gap: 8px; align-items: center; }}
  .cat-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}
  .cat-val {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--text); }}

  .findings {{ list-style: none; display: flex; flex-direction: column; gap: 6px; }}
  .finding {{ display: flex; align-items: flex-start; gap: 8px; font-size: 12px; line-height: 1.5; }}
  .dot {{ width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-top: 5px; }}
  .pass-dot {{ background: var(--green); }}
  .fail-dot {{ background: var(--red); }}
  .pass {{ color: var(--muted); }}
  .fail {{ color: var(--text); }}

  footer {{ padding: 32px 48px; border-top: 1px solid var(--border); color: var(--muted); font-family: 'IBM Plex Mono', monospace; font-size: 11px; }}
</style>
</head>
<body>
<header>
  <span class="header-title">cuda-sample-quality-analyzer</span>
  <span class="header-sub">static analysis report — {len(analyses)} sample(s)</span>
</header>
<main>
  <h2>Score Summary</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Sample</th><th>Total / 100</th>{cat_headers}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <h2>Sample Details</h2>
  <div class="cards">{cards}</div>
</main>
<footer>generated by cuda-sample-quality-analyzer · rule-based static analysis</footer>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
