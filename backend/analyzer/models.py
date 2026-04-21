from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class RuleResult:
    rule_id: str
    category: str
    passed: bool
    score: float
    max_score: float
    message: str
    severity: str = "info"


@dataclass
class SampleFiles:
    name: str
    path: str
    lang: str = "cuda"          # "cuda" | "python" | "cpp"
    cuda_files: List[str] = field(default_factory=list)
    python_files: List[str] = field(default_factory=list)
    cpp_files: List[str] = field(default_factory=list)
    readme_files: List[str] = field(default_factory=list)
    cmake_files: List[str] = field(default_factory=list)
    requirements_files: List[str] = field(default_factory=list)
    other_files: List[str] = field(default_factory=list)


@dataclass
class SampleAnalysis:
    sample_name: str
    sample_path: str
    lang: str
    category_scores: Dict[str, float]
    category_max_scores: Dict[str, float]
    total_score: float
    total_max_score: float
    rule_results: List[RuleResult]
    summary: List[str]
