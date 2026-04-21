from __future__ import annotations
import re
from typing import List
from analyzer.models import RuleResult, SampleFiles
from analyzer.scanner import read_text_file

# ── Shared patterns ──────────────────────────────────────────────────────────
BUILD_PATTERNS    = [r"\bcmake\b", r"\bmake\b", r"\bnvcc\b", r"\bbuild\b", r"\bpip install\b", r"\bsetup\.py\b"]
RUN_PATTERNS      = [r"\brun\b", r"\bexecute\b", r"\./\w+", r"\bpython\b.*\.py", r"\bpython3\b"]
OUTPUT_PATTERNS   = [r"expected output", r"sample output", r"output:", r"result:", r"example output"]

# ── CUDA C patterns ──────────────────────────────────────────────────────────
CUDA_ERROR_PATTERNS   = [r"cudaGetLastError\s*\(", r"cudaPeekAtLastError\s*\(",
                          r"checkCudaErrors\s*\(", r"CUDA_CHECK\s*\(", r"CHECK_CUDA\s*\("]
CUDA_FREE_PATTERNS    = [r"cudaFree\s*\(", r"cudaFreeHost\s*\("]
KERNEL_LAUNCH_PAT     = r"<<<.*>>>"
SYNC_PATTERNS         = [r"cudaDeviceSynchronize\s*\(", r"cudaStreamSynchronize\s*\("]
OUTDATED_PATTERNS     = [r"CUDA 4\.0", r"CC 2\.0", r"\bsm_20\b", r"\bsm_21\b", r"\bG80\b"]
MODERN_CUDA_PATTERNS  = [r"cooperative_groups", r"cudaMallocAsync\s*\(", r"__shfl", r"\bhalf\b",
                          r"cudaMemPrefetchAsync\s*\("]

# ── Python GPU patterns ──────────────────────────────────────────────────────
PY_GPU_LIBS           = [r"\bcupy\b", r"\bnumba\.cuda\b", r"\bpycuda\b", r"\btorch\.cuda\b",
                          r"\btensorflow\b", r"\bjax\b", r"\btriton\b"]
PY_ERROR_PATTERNS     = [r"try\s*:", r"except\s+\w*Error", r"except\s+Exception"]
PY_DOCSTRING_PAT      = r'"""[\s\S]*?"""'
PY_TYPE_HINTS         = [r"def \w+\(.*:.*\)\s*->", r":\s*(int|float|str|bool|List|Dict|Optional|Tuple)"]
PY_MODERN_PATTERNS    = [r"@torch\.jit\.script", r"torch\.compile", r"cp\.cuda\.Stream",
                          r"numba\.cuda\.jit", r"triton\.jit"]
PY_MEMORY_PATTERNS    = [r"\.free\(\)", r"del \w+", r"torch\.cuda\.empty_cache", r"cp\.get_default_memory_pool"]

# ── C++ patterns ─────────────────────────────────────────────────────────────
CPP_ERROR_PATTERNS    = [r"throw\s+\w+", r"try\s*\{", r"catch\s*\(", r"assert\s*\(", r"static_assert"]
CPP_MEMORY_PATTERNS   = [r"\bdelete\b", r"\.reset\(\)", r"unique_ptr", r"shared_ptr", r"make_unique", r"make_shared"]
CPP_MODERN_PATTERNS   = [r"auto\s+\w+\s*=", r"nullptr", r"constexpr", r"std::move", r"std::forward",
                          r"#include\s*<memory>", r"std::unique_ptr", r"std::shared_ptr"]
CPP_OUTDATED_PATTERNS = [r"\bNULL\b", r"malloc\s*\(", r"free\s*\(", r"printf\s*\("]


def _concat(paths):
    return "\n\n".join(read_text_file(p) for p in paths)


def _found(patterns, text):
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def _comment_ratio(code: str, lang: str) -> float:
    lines = code.splitlines()
    total = max(len(lines), 1)
    if lang == "python":
        comments = sum(1 for l in lines if l.strip().startswith("#"))
        docstrings = len(re.findall(r'"""[\s\S]*?"""', code))
        return (comments + docstrings * 3) / total
    else:
        comments = sum(
            1 for l in lines
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("*")
        )
        return comments / total


# ─────────────────────────────────────────────────────────────────────────────
# CUDA rules
# ─────────────────────────────────────────────────────────────────────────────
def _rules_cuda(sample: SampleFiles) -> List[RuleResult]:
    results = []
    readme  = _concat(sample.readme_files)
    cuda    = _concat(sample.cuda_files)
    cmake   = _concat(sample.cmake_files)
    all_txt = "\n".join([readme, cuda, cmake])

    # Documentation (25)
    readme_ok = bool(sample.readme_files)
    results.append(RuleResult("DOC_README",    "Documentation", readme_ok,
        5.0 if readme_ok else 0.0, 5.0,
        "README exists" if readme_ok else "README missing", "info" if readme_ok else "warning"))

    build_ok = _found(BUILD_PATTERNS, readme)
    results.append(RuleResult("DOC_BUILD",     "Documentation", build_ok,
        5.0 if build_ok else 0.0, 5.0,
        "Build instructions found" if build_ok else "Build instructions missing", "warning"))

    run_ok = _found(RUN_PATTERNS, readme)
    results.append(RuleResult("DOC_RUN",       "Documentation", run_ok,
        5.0 if run_ok else 0.0, 5.0,
        "Run instructions found" if run_ok else "Run instructions missing", "warning"))

    out_ok = _found(OUTPUT_PATTERNS, readme)
    results.append(RuleResult("DOC_OUTPUT",    "Documentation", out_ok,
        5.0 if out_ok else 0.0, 5.0,
        "Expected output described" if out_ok else "Expected output not described", "info"))

    concept_ok = any(k in readme.lower() for k in ["api", "concept", "stream", "kernel", "demonstrates", "covers"])
    results.append(RuleResult("DOC_CONCEPTS",  "Documentation", concept_ok,
        5.0 if concept_ok else 0.0, 5.0,
        "Concepts/APIs described" if concept_ok else "Concepts/APIs not described", "info"))

    # Clarity (25)
    ratio = _comment_ratio(cuda, "cuda")
    cscore = 10.0 if ratio >= 0.10 else (6.0 if ratio >= 0.05 else 0.0)
    results.append(RuleResult("CLARITY_COMMENTS", "Clarity", ratio >= 0.05, cscore, 10.0,
        f"Comment ratio: {ratio:.1%}", "info"))

    kernels  = re.findall(r"__global__\s+void\s+([A-Za-z_]\w*)", cuda)
    readable = [k for k in kernels if len(k) >= 4 and ("_" in k or any(c.isupper() for c in k[1:]))]
    names_ok = (not kernels) or (len(readable) >= len(kernels) / 2)
    results.append(RuleResult("CLARITY_KERNEL_NAMES", "Clarity", names_ok,
        5.0 if names_ok else 2.0, 5.0,
        "Kernel names look descriptive" if names_ok else "Kernel names may be too terse", "info"))

    lines = max(len(cuda.splitlines()), 1)
    size_score = 10.0 if lines <= 150 else (7.0 if lines <= 300 else 3.0)
    results.append(RuleResult("CLARITY_SIZE", "Clarity", lines <= 300, size_score, 10.0,
        f"CUDA source: {lines} lines", "info"))

    # Best Practices (30)
    err_ok = _found(CUDA_ERROR_PATTERNS, cuda)
    results.append(RuleResult("BP_ERROR",  "Best Practices", err_ok,
        10.0 if err_ok else 0.0, 10.0,
        "CUDA error checking found" if err_ok else "CUDA error checking not detected", "warning"))

    free_ok = _found(CUDA_FREE_PATTERNS, cuda)
    results.append(RuleResult("BP_MEMORY", "Best Practices", free_ok,
        10.0 if free_ok else 0.0, 10.0,
        "Device memory freed" if free_ok else "cudaFree not detected — possible memory leak", "warning"))

    has_launch = bool(re.search(KERNEL_LAUNCH_PAT, cuda, re.DOTALL))
    has_sync   = _found(SYNC_PATTERNS, cuda)
    sync_ok    = (not has_launch) or has_sync or err_ok
    results.append(RuleResult("BP_SYNC",   "Best Practices", sync_ok,
        10.0 if sync_ok else 3.0, 10.0,
        "Sync/error capture after kernel launch" if sync_ok else "Kernel launch without sync/error capture", "warning"))

    # Modernity (20)
    outdated = _found(OUTDATED_PATTERNS, all_txt)
    results.append(RuleResult("MOD_NO_OUTDATED", "Modernity", not outdated,
        10.0 if not outdated else 2.0, 10.0,
        "No outdated terminology" if not outdated else "Outdated CUDA terminology detected (e.g. sm_20, CUDA 4.0)",
        "warning" if outdated else "info"))

    modern = _found(MODERN_CUDA_PATTERNS, cuda)
    results.append(RuleResult("MOD_MODERN", "Modernity", modern,
        10.0 if modern else 5.0, 10.0,
        "Modern CUDA APIs detected" if modern else "No strong modern CUDA patterns found", "info"))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Python GPU rules
# ─────────────────────────────────────────────────────────────────────────────
def _rules_python(sample: SampleFiles) -> List[RuleResult]:
    results = []
    readme  = _concat(sample.readme_files)
    py      = _concat(sample.python_files)
    reqs    = _concat(sample.requirements_files)
    all_txt = "\n".join([readme, py, reqs])

    # Documentation (25)
    readme_ok = bool(sample.readme_files)
    results.append(RuleResult("DOC_README",    "Documentation", readme_ok,
        5.0 if readme_ok else 0.0, 5.0,
        "README exists" if readme_ok else "README missing", "info" if readme_ok else "warning"))

    build_ok = _found(BUILD_PATTERNS, readme) or bool(sample.requirements_files)
    results.append(RuleResult("DOC_INSTALL",   "Documentation", build_ok,
        5.0 if build_ok else 0.0, 5.0,
        "Install instructions found" if build_ok else "Install instructions missing", "warning"))

    run_ok = _found(RUN_PATTERNS, readme)
    results.append(RuleResult("DOC_RUN",       "Documentation", run_ok,
        5.0 if run_ok else 0.0, 5.0,
        "Run instructions found" if run_ok else "Run instructions missing", "warning"))

    out_ok = _found(OUTPUT_PATTERNS, readme)
    results.append(RuleResult("DOC_OUTPUT",    "Documentation", out_ok,
        5.0 if out_ok else 0.0, 5.0,
        "Expected output described" if out_ok else "Expected output not described", "info"))

    docstring_ok = bool(re.search(PY_DOCSTRING_PAT, py))
    results.append(RuleResult("DOC_DOCSTRINGS", "Documentation", docstring_ok,
        5.0 if docstring_ok else 0.0, 5.0,
        "Docstrings found in code" if docstring_ok else "No docstrings detected", "info"))

    # Clarity (25)
    ratio = _comment_ratio(py, "python")
    cscore = 10.0 if ratio >= 0.12 else (6.0 if ratio >= 0.06 else 0.0)
    results.append(RuleResult("CLARITY_COMMENTS", "Clarity", ratio >= 0.06, cscore, 10.0,
        f"Comment/docstring ratio: {ratio:.1%}", "info"))

    type_ok = _found(PY_TYPE_HINTS, py)
    results.append(RuleResult("CLARITY_TYPE_HINTS", "Clarity", type_ok,
        8.0 if type_ok else 3.0, 8.0,
        "Type hints used" if type_ok else "No type hints detected", "info"))

    lines = max(len(py.splitlines()), 1)
    size_score = 7.0 if lines <= 200 else (5.0 if lines <= 500 else 2.0)
    results.append(RuleResult("CLARITY_SIZE", "Clarity", lines <= 500, size_score, 7.0,
        f"Python source: {lines} lines", "info"))

    # Best Practices (30)
    gpu_ok = _found(PY_GPU_LIBS, py)
    results.append(RuleResult("BP_GPU_LIB", "Best Practices", gpu_ok,
        10.0 if gpu_ok else 0.0, 10.0,
        "GPU library usage detected (cupy/numba/torch.cuda/etc)" if gpu_ok else "No GPU library usage detected", "warning"))

    err_ok = _found(PY_ERROR_PATTERNS, py)
    results.append(RuleResult("BP_ERROR_HANDLING", "Best Practices", err_ok,
        10.0 if err_ok else 0.0, 10.0,
        "Error handling (try/except) found" if err_ok else "No error handling detected", "warning"))

    mem_ok = _found(PY_MEMORY_PATTERNS, py)
    results.append(RuleResult("BP_MEMORY", "Best Practices", mem_ok,
        10.0 if mem_ok else 3.0, 10.0,
        "Memory cleanup patterns found" if mem_ok else "No explicit memory cleanup detected", "info"))

    # Modernity (20)
    modern = _found(PY_MODERN_PATTERNS, py)
    results.append(RuleResult("MOD_MODERN", "Modernity", modern,
        10.0 if modern else 5.0, 10.0,
        "Modern GPU Python patterns detected" if modern else "No strong modern GPU patterns found", "info"))

    has_reqs = bool(sample.requirements_files)
    results.append(RuleResult("MOD_REQUIREMENTS", "Modernity", has_reqs,
        10.0 if has_reqs else 3.0, 10.0,
        "requirements.txt / pyproject.toml found" if has_reqs else "No dependency file found", "info"))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# C++ rules
# ─────────────────────────────────────────────────────────────────────────────
def _rules_cpp(sample: SampleFiles) -> List[RuleResult]:
    results = []
    readme  = _concat(sample.readme_files)
    cpp     = _concat(sample.cpp_files)
    cmake   = _concat(sample.cmake_files)
    all_txt = "\n".join([readme, cpp, cmake])

    # Documentation (25)
    readme_ok = bool(sample.readme_files)
    results.append(RuleResult("DOC_README",  "Documentation", readme_ok,
        5.0 if readme_ok else 0.0, 5.0,
        "README exists" if readme_ok else "README missing", "info" if readme_ok else "warning"))

    build_ok = _found(BUILD_PATTERNS, readme) or bool(sample.cmake_files)
    results.append(RuleResult("DOC_BUILD",   "Documentation", build_ok,
        5.0 if build_ok else 0.0, 5.0,
        "Build instructions found" if build_ok else "Build instructions missing", "warning"))

    run_ok = _found(RUN_PATTERNS, readme)
    results.append(RuleResult("DOC_RUN",     "Documentation", run_ok,
        5.0 if run_ok else 0.0, 5.0,
        "Run instructions found" if run_ok else "Run instructions missing", "warning"))

    out_ok = _found(OUTPUT_PATTERNS, readme)
    results.append(RuleResult("DOC_OUTPUT",  "Documentation", out_ok,
        5.0 if out_ok else 0.0, 5.0,
        "Expected output described" if out_ok else "Expected output not described", "info"))

    concept_ok = any(k in readme.lower() for k in ["api", "concept", "demonstrates", "covers", "overview"])
    results.append(RuleResult("DOC_CONCEPTS","Documentation", concept_ok,
        5.0 if concept_ok else 0.0, 5.0,
        "Concepts described" if concept_ok else "Concepts not described", "info"))

    # Clarity (25)
    ratio = _comment_ratio(cpp, "cpp")
    cscore = 10.0 if ratio >= 0.10 else (6.0 if ratio >= 0.05 else 0.0)
    results.append(RuleResult("CLARITY_COMMENTS", "Clarity", ratio >= 0.05, cscore, 10.0,
        f"Comment ratio: {ratio:.1%}", "info"))

    lines = max(len(cpp.splitlines()), 1)
    size_score = 10.0 if lines <= 200 else (7.0 if lines <= 500 else 3.0)
    results.append(RuleResult("CLARITY_SIZE", "Clarity", lines <= 500, size_score, 10.0,
        f"C++ source: {lines} lines", "info"))

    cmake_ok = bool(sample.cmake_files)
    results.append(RuleResult("CLARITY_CMAKE", "Clarity", cmake_ok,
        5.0 if cmake_ok else 0.0, 5.0,
        "CMakeLists.txt present" if cmake_ok else "No CMakeLists.txt", "info"))

    # Best Practices (30)
    err_ok = _found(CPP_ERROR_PATTERNS, cpp)
    results.append(RuleResult("BP_ERROR",  "Best Practices", err_ok,
        10.0 if err_ok else 0.0, 10.0,
        "Error handling found (try/catch/assert)" if err_ok else "No error handling detected", "warning"))

    mem_ok = _found(CPP_MEMORY_PATTERNS, cpp)
    results.append(RuleResult("BP_MEMORY", "Best Practices", mem_ok,
        10.0 if mem_ok else 0.0, 10.0,
        "Smart pointers / RAII patterns found" if mem_ok else "No smart pointer or RAII patterns detected", "warning"))

    raw_mem = _found([r"\bmalloc\s*\(", r"\bnew\b"], cpp)
    results.append(RuleResult("BP_NO_RAW_ALLOC", "Best Practices", not raw_mem,
        10.0 if not raw_mem else 3.0, 10.0,
        "No raw malloc/new detected" if not raw_mem else "Raw malloc/new used — prefer RAII", "info"))

    # Modernity (20)
    modern = _found(CPP_MODERN_PATTERNS, cpp)
    results.append(RuleResult("MOD_MODERN", "Modernity", modern,
        10.0 if modern else 3.0, 10.0,
        "Modern C++ patterns detected (auto, nullptr, smart ptrs)" if modern else "No modern C++ patterns detected", "warning"))

    outdated = _found(CPP_OUTDATED_PATTERNS, cpp)
    results.append(RuleResult("MOD_NO_OUTDATED", "Modernity", not outdated,
        10.0 if not outdated else 4.0, 10.0,
        "No legacy C patterns detected" if not outdated else "Legacy C patterns detected (NULL, malloc, printf)", "info"))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_rules(sample: SampleFiles) -> List[RuleResult]:
    if sample.lang == "cuda":
        return _rules_cuda(sample)
    elif sample.lang == "python":
        return _rules_python(sample)
    elif sample.lang == "cpp":
        return _rules_cpp(sample)
    # Mixed: cuda takes priority
    return _rules_cuda(sample)
