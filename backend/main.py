from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import tempfile
import shutil
import os
import re
from dataclasses import asdict

from analyzer.scanner import collect_sample_dirs
from analyzer.rules import evaluate_rules
from analyzer.scoring import score_sample

app = FastAPI(title="CUDA Sample Quality Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SKIP_DIRS = {"src", "inc", "common", "utils", "include", "lib", "deps", "third_party"}

class AnalyzeRequest(BaseModel):
    repo_url: str

def is_valid_github_url(url: str) -> bool:
    return bool(re.match(r"https://github\.com/[\w\-\.]+/[\w\-\.]+", url))

@app.get("/")
def root():
    return {"status": "ok", "service": "cuda-sample-quality-analyzer"}

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    if not is_valid_github_url(req.repo_url):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            ["git", "clone", "--depth=1", req.repo_url, tmpdir],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=f"Clone failed: {result.stderr[:300]}")

        samples = collect_sample_dirs(tmpdir)

        # Filter out utility dirs
        samples = [s for s in samples if s.name.lower() not in SKIP_DIRS]

        if not samples:
            raise HTTPException(status_code=404, detail="No CUDA sample directories found (.cu/.cuh files required)")

        analyses = []
        for sample in samples:
            rules = evaluate_rules(sample)
            analysis = score_sample(sample, rules)
            analyses.append(asdict(analysis))

        analyses.sort(key=lambda a: a["total_score"], reverse=True)

        # Summary stats
        scores = [a["total_score"] for a in analyses]
        avg = round(sum(scores) / len(scores), 1)
        cats = ["Documentation", "Clarity", "Best Practices", "Modernity"]
        cat_avgs = {
            cat: round(sum(a["category_scores"].get(cat, 0) for a in analyses) / len(analyses), 1)
            for cat in cats
        }

        grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for s in scores:
            if s >= 85: grade_dist["A"] += 1
            elif s >= 70: grade_dist["B"] += 1
            elif s >= 55: grade_dist["C"] += 1
            elif s >= 40: grade_dist["D"] += 1
            else: grade_dist["F"] += 1

        return {
            "repo_url": req.repo_url,
            "repo_name": req.repo_url.rstrip("/").split("/")[-1],
            "total_samples": len(analyses),
            "average_score": avg,
            "category_averages": cat_avgs,
            "grade_distribution": grade_dist,
            "samples": analyses,
        }

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
