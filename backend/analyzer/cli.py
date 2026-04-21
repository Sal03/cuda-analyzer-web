from __future__ import annotations
import argparse, sys

from analyzer.scanner import collect_sample_dirs
from analyzer.rules import evaluate_rules
from analyzer.scoring import score_sample
from analyzer.report import write_json_report, write_csv_report, write_html_report

def _color(score):
    if score >= 85: return "\033[92m"
    if score >= 70: return "\033[96m"
    if score >= 55: return "\033[93m"
    return "\033[91m"

LANG_TAG = {"cuda": "\033[94m[cu]\033[0m", "python": "\033[93m[py]\033[0m",
            "cpp": "\033[96m[c+]\033[0m", "unknown": "\033[90m[??]\033[0m"}
RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"

def run_analysis(root, json_path, csv_path, html_path):
    samples = collect_sample_dirs(root)
    if not samples:
        print("No sample directories found (.cu/.cuh, .py, .cpp files required).")
        sys.exit(1)

    analyses = []
    for sample in samples:
        rules = evaluate_rules(sample)
        analyses.append(score_sample(sample, rules))

    analyses.sort(key=lambda a: a.total_score, reverse=True)
    cats = ["Documentation", "Clarity", "Best Practices", "Modernity"]
    col_w = 15

    header = f"{'Sample':<22} {'Lang':>5}  {'Total':>7}  " + "  ".join(f"{c[:col_w]:<{col_w}}" for c in cats)
    print(f"\n{BOLD}GPU Code Quality Analyzer{RESET}")
    print("─" * len(header))
    print(f"{BOLD}{header}{RESET}")
    print("─" * len(header))

    for a in analyses:
        c = _color(a.total_score)
        tag = LANG_TAG.get(a.lang, "")
        cat_str = "  ".join(f"{a.category_scores.get(cat,0):>{col_w}.1f}" for cat in cats)
        print(f"{a.sample_name:<22} {tag}  {c}{a.total_score:>6.1f}{RESET}  {DIM}{cat_str}{RESET}")

    print("─" * len(header))
    print()

    for a in analyses:
        c = _color(a.total_score)
        tag = LANG_TAG.get(a.lang, "")
        print(f"{BOLD}{c}{a.sample_name}{RESET} {tag}  —  {c}{a.total_score:.1f}/100{RESET}")
        for item in a.summary:
            print(f"  • {item}")
        print()

    if json_path:
        write_json_report(json_path, analyses); print(f"  JSON → {json_path}")
    if csv_path:
        write_csv_report(csv_path, analyses);  print(f"  CSV  → {csv_path}")
    if html_path:
        write_html_report(html_path, analyses); print(f"  HTML → {html_path}")

    lang_counts = {}
    for a in analyses:
        lang_counts[a.lang] = lang_counts.get(a.lang, 0) + 1
    print(f"\nDetected: " + " | ".join(f"{v}x {k}" for k, v in sorted(lang_counts.items())))

def main():
    p = argparse.ArgumentParser(description="GPU Code Quality Analyzer (CUDA / Python / C++)")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("root")
    a.add_argument("--json", dest="json_path")
    a.add_argument("--csv",  dest="csv_path")
    a.add_argument("--html", dest="html_path")
    args = p.parse_args()
    if args.cmd == "analyze":
        run_analysis(args.root, args.json_path, args.csv_path, args.html_path)

if __name__ == "__main__":
    main()
