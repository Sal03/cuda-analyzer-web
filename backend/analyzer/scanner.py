from __future__ import annotations
import os
from typing import List
from analyzer.models import SampleFiles

README_NAMES = {"readme", "readme.md", "readme.txt", "readme.rst"}
SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", "build", "dist", ".eggs"}


def is_readme(filename: str) -> bool:
    return filename.lower() in README_NAMES or filename.lower().startswith("readme")


def _detect_lang(cuda, python, cpp) -> str:
    if cuda:
        return "cuda"
    if cpp and not python:
        return "cpp"
    if python:
        return "python"
    return "unknown"


def collect_sample_dirs(root: str) -> List[SampleFiles]:
    samples: List[SampleFiles] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        cuda_files, python_files, cpp_files = [], [], []
        readme_files, cmake_files, requirements_files, other_files = [], [], [], []
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            lower = filename.lower()
            if lower.endswith(".cu") or lower.endswith(".cuh"):
                cuda_files.append(full_path)
            elif lower.endswith(".py"):
                python_files.append(full_path)
            elif lower.endswith((".cpp", ".hpp", ".h", ".cc")):
                cpp_files.append(full_path)
            elif is_readme(filename):
                readme_files.append(full_path)
            elif lower == "cmakelists.txt":
                cmake_files.append(full_path)
            elif lower in ("requirements.txt", "setup.py", "setup.cfg", "pyproject.toml"):
                requirements_files.append(full_path)
            else:
                other_files.append(full_path)
        if not (cuda_files or python_files or cpp_files):
            continue
        lang = _detect_lang(cuda_files, python_files, cpp_files)
        samples.append(SampleFiles(
            name=os.path.basename(dirpath),
            path=dirpath,
            lang=lang,
            cuda_files=sorted(cuda_files),
            python_files=sorted(python_files),
            cpp_files=sorted(cpp_files),
            readme_files=sorted(readme_files),
            cmake_files=sorted(cmake_files),
            requirements_files=sorted(requirements_files),
            other_files=sorted(other_files),
        ))
    return sorted(samples, key=lambda s: s.path)


def read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""
