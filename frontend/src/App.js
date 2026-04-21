import { useState } from "react";
import "./App.css";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const CATS = ["Documentation", "Clarity", "Best Practices", "Modernity"];
const CAT_MAX = { Documentation: 25, Clarity: 25, "Best Practices": 30, Modernity: 20 };

function grade(score) {
  if (score >= 85) return "A";
  if (score >= 70) return "B";
  if (score >= 55) return "C";
  if (score >= 40) return "D";
  return "F";
}

function gradeClass(score) {
  if (score >= 85) return "grade-a";
  if (score >= 70) return "grade-b";
  if (score >= 55) return "grade-c";
  return "grade-f";
}

function ScoreBar({ value, max }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div className="bar-wrap">
      <div className="bar-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

function StatCard({ label, value, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function GradeBar({ dist, total }) {
  const grades = ["A", "B", "C", "D", "F"];
  const colors = { A: "#39d353", B: "#76e3c4", C: "#e3b341", D: "#f0883e", F: "#f85149" };
  return (
    <div className="grade-bar-wrap">
      {grades.map(g => {
        const count = dist[g] || 0;
        const pct = total > 0 ? (count / total) * 100 : 0;
        return pct > 0 ? (
          <div
            key={g}
            className="grade-segment"
            style={{ width: `${pct}%`, background: colors[g] }}
            title={`${g}: ${count} samples`}
          >
            {pct > 8 && <span>{g}</span>}
          </div>
        ) : null;
      })}
    </div>
  );
}

function SampleCard({ sample, index }) {
  const [open, setOpen] = useState(false);
  const g = grade(sample.total_score);
  const gc = gradeClass(sample.total_score);
  const warnings = sample.rule_results.filter(r => !r.passed);
  const passes = sample.rule_results.filter(r => r.passed);

  return (
    <div className={`sample-card ${open ? "open" : ""}`} style={{ animationDelay: `${index * 30}ms` }}>
      <div className="sample-card-header" onClick={() => setOpen(o => !o)}>
        <span className="sample-card-name">{sample.sample_name}</span>
        <div className="sample-card-right">
          <div className="sample-cat-pills">
            {CATS.map(c => (
              <div key={c} className="mini-pill">
                <span className="mini-label">{c.split(" ")[0]}</span>
                <span className="mini-val">{(sample.category_scores[c] || 0).toFixed(0)}</span>
              </div>
            ))}
          </div>
          <span className={`score-badge ${gc}`}>
            {sample.total_score.toFixed(0)}<sup>{g}</sup>
          </span>
          <span className={`chevron ${open ? "up" : ""}`}>›</span>
        </div>
      </div>
      {open && (
        <div className="sample-card-body">
          <div className="findings-grid">
            <div className="findings-col">
              <div className="findings-heading fail-heading">Issues</div>
              {warnings.length === 0
                ? <div className="no-issues">No issues found</div>
                : warnings.map(r => (
                  <div key={r.rule_id} className="finding fail">
                    <span className="dot fail-dot" />
                    {r.message}
                  </div>
                ))}
            </div>
            <div className="findings-col">
              <div className="findings-heading pass-heading">Passing</div>
              {passes.map(r => (
                <div key={r.rule_id} className="finding pass">
                  <span className="dot pass-dot" />
                  {r.message}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ResultsDashboard({ data }) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sortBy, setSortBy] = useState("score");

  let samples = data.samples.filter(s => {
    const matchSearch = s.sample_name.toLowerCase().includes(search.toLowerCase());
    const matchFilter =
      filter === "all" ||
      (filter === "issues" && s.rule_results.some(r => !r.passed && r.severity === "warning")) ||
      (filter === "strong" && s.total_score >= 85) ||
      (filter === "weak" && s.total_score < 55);
    return matchSearch && matchFilter;
  });

  if (sortBy === "score") samples = [...samples].sort((a, b) => b.total_score - a.total_score);
  else if (sortBy === "name") samples = [...samples].sort((a, b) => a.sample_name.localeCompare(b.sample_name));
  else if (sortBy === "docs") samples = [...samples].sort((a, b) => (b.category_scores["Documentation"] || 0) - (a.category_scores["Documentation"] || 0));

  return (
    <div className="results">
      {/* Repo header */}
      <div className="repo-header">
        <div className="repo-title">
          <span className="repo-icon">⬡</span>
          <span className="repo-name">{data.repo_name}</span>
        </div>
        <a href={data.repo_url} target="_blank" rel="noopener noreferrer" className="repo-link">
          {data.repo_url.replace("https://", "")} ↗
        </a>
      </div>

      {/* Stats row */}
      <div className="stats-row">
        <StatCard label="Samples Analyzed" value={data.total_samples} />
        <StatCard label="Average Score" value={`${data.average_score}/100`} sub={`Grade ${grade(data.average_score)}`} />
        {CATS.map(c => (
          <StatCard key={c} label={c} value={`${data.category_averages[c]}/${CAT_MAX[c]}`} />
        ))}
      </div>

      {/* Grade distribution */}
      <div className="section">
        <div className="section-label">Grade Distribution</div>
        <GradeBar dist={data.grade_distribution} total={data.total_samples} />
        <div className="grade-legend">
          {["A", "B", "C", "D", "F"].map(g => (
            <span key={g} className="legend-item">
              <span className={`legend-dot grade-dot-${g.toLowerCase()}`} />
              {g}: {data.grade_distribution[g] || 0}
            </span>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="controls">
        <input
          className="search-input"
          placeholder="Search samples..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div className="filter-group">
          {[["all", "All"], ["strong", "A (85+)"], ["issues", "Has Issues"], ["weak", "Low (<55)"]].map(([val, label]) => (
            <button
              key={val}
              className={`filter-btn ${filter === val ? "active" : ""}`}
              onClick={() => setFilter(val)}
            >{label}</button>
          ))}
        </div>
        <select className="sort-select" value={sortBy} onChange={e => setSortBy(e.target.value)}>
          <option value="score">Sort: Score</option>
          <option value="name">Sort: Name</option>
          <option value="docs">Sort: Docs</option>
        </select>
      </div>

      {/* Sample count */}
      <div className="results-count">{samples.length} sample{samples.length !== 1 ? "s" : ""}</div>

      {/* Sample cards */}
      <div className="samples-list">
        {samples.map((s, i) => (
          <SampleCard key={s.sample_name + s.sample_path} sample={s} index={i} />
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  async function handleAnalyze() {
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    setData(null);
    try {
      const res = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url.trim() }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Analysis failed");
      setData(json);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-mark">▣</span>
            <span className="logo-text">cuda-sample-quality-analyzer</span>
          </div>
          <p className="header-tagline">
            Rule-based static analysis for CUDA sample repositories
          </p>
        </div>
      </header>

      <main className="app-main">
        <div className="input-section">
          <div className="input-wrap">
            <input
              className="repo-input"
              type="text"
              placeholder="https://github.com/NVIDIA/cuda-samples"
              value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleAnalyze()}
            />
            <button
              className={`analyze-btn ${loading ? "loading" : ""}`}
              onClick={handleAnalyze}
              disabled={loading || !url.trim()}
            >
              {loading ? (
                <span className="spinner-wrap"><span className="spinner" /> Analyzing…</span>
              ) : "Analyze →"}
            </button>
          </div>
          {error && <div className="error-msg">⚠ {error}</div>}
          {loading && (
            <div className="loading-steps">
              <span className="loading-step">Cloning repository…</span>
              <span className="loading-step">Scanning CUDA files…</span>
              <span className="loading-step">Running quality rules…</span>
            </div>
          )}
        </div>

        {data && <ResultsDashboard data={data} />}

        {!data && !loading && (
          <div className="empty-state">
            <div className="empty-grid">
              {["Documentation", "Clarity", "Best Practices", "Modernity"].map(c => (
                <div key={c} className="empty-card">
                  <div className="empty-card-label">{c}</div>
                  <div className="empty-card-desc">
                    {c === "Documentation" && "README, build & run instructions, expected output"}
                    {c === "Clarity" && "Comment density, kernel naming, file length"}
                    {c === "Best Practices" && "Error checks, memory cleanup, sync after launch"}
                    {c === "Modernity" && "Outdated APIs, legacy terminology, modern patterns"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        generated by cuda-sample-quality-analyzer · rule-based static analysis
      </footer>
    </div>
  );
}
