from __future__ import annotations
from collections import defaultdict
from typing import Dict, List
from analyzer.models import RuleResult, SampleAnalysis, SampleFiles

CATEGORY_WEIGHTS = {
    "Documentation": 25.0,
    "Clarity": 25.0,
    "Best Practices": 30.0,
    "Modernity": 20.0,
}


def score_sample(sample: SampleFiles, rule_results: List[RuleResult]) -> SampleAnalysis:
    cat_scores: Dict[str, float] = defaultdict(float)
    cat_max: Dict[str, float] = defaultdict(float)

    for r in rule_results:
        if r.category in CATEGORY_WEIGHTS:
            cat_scores[r.category] += r.score
            cat_max[r.category] += r.max_score

    weighted: Dict[str, float] = {}
    total = 0.0

    for cat, weight in CATEGORY_WEIGHTS.items():
        raw = cat_scores.get(cat, 0.0)
        mx = cat_max.get(cat, 1.0)
        norm = (raw / mx) if mx > 0 else 0.0
        w = round(norm * weight, 2)
        weighted[cat] = w
        total += w

    total = round(total, 2)

    summary = []
    if total >= 85:   summary.append("Strong overall quality")
    elif total >= 70: summary.append("Good quality with minor gaps")
    elif total >= 55: summary.append("Moderate quality — several areas need improvement")
    else:             summary.append("Needs significant improvement")

    warnings = [r.message for r in rule_results if not r.passed and r.severity == "warning"]
    summary.extend(warnings[:4])

    return SampleAnalysis(
        sample_name=sample.name,
        sample_path=sample.path,
        lang=sample.lang,
        category_scores=weighted,
        category_max_scores=dict(CATEGORY_WEIGHTS),
        total_score=total,
        total_max_score=100.0,
        rule_results=rule_results,
        summary=summary,
    )
