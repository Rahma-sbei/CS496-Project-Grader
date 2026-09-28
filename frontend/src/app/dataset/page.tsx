"use client";

import { useEffect, useState } from "react";
import { api, Category, DashboardData } from "@/lib/api";

export default function DatasetPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [running, setRunning] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [limit, setLimit] = useState<string>("");
  const [dataset, setDataset] = useState("data/golden_set.jsonl");

  function load() {
    api.getCategories().then((d) => setCategories(d.categories));
    api.getStatistics().then(setDashboard).catch(() => {});
  }

  useEffect(load, []);

  async function handleRun() {
    setRunning(true);
    setRunMessage(null);
    try {
      const res = await api.runEvaluation({
        dataset,
        limit: limit ? parseInt(limit, 10) : undefined,
      });
      setRunMessage(
        `Run "${res.output_name}" complete — ${res.n_results} items, average score ${res.statistics.average_total_score ?? "—"}/10.`
      );
      load();
    } catch (e: any) {
      setRunMessage(`Run failed: ${e.message}`);
    } finally {
      setRunning(false);
    }
  }

  const counts = dashboard?.dataset || {};

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Dataset</h1>
        <p className="text-muted mt-1">
          The golden dataset backing the evaluation harness — generated deterministically from the
          scenario catalog, split into development and test sets.
        </p>
      </div>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Golden set" value={counts.golden_set ?? "—"} />
        <Stat label="Development items" value={counts.dev ?? "—"} />
        <Stat label="Test items" value={counts.test ?? "—"} />
        <Stat
          label="Failed / dropped"
          value={dashboard?.performance.failed_items ?? "—"}
        />
      </section>

      <section className="bg-panel border border-line rounded-card shadow-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-ink">Run the evaluation harness</h2>
        <p className="text-sm text-muted">
          Equivalent to running <code className="font-mono text-xs bg-paper px-1 py-0.5 rounded">python run_eval.py</code> from
          the command line. Runs generation + judging for every item in the chosen dataset file and
          writes results to <code className="font-mono text-xs bg-paper px-1 py-0.5 rounded">results/</code>.
        </p>
        <div className="flex flex-wrap gap-3 items-end">
          <label className="text-sm">
            <span className="block text-xs font-medium text-muted mb-1">Dataset file</span>
            <select
              className="input"
              value={dataset}
              onChange={(e) => setDataset(e.target.value)}
            >
              <option value="data/golden_set.jsonl">golden_set.jsonl (all items)</option>
              <option value="data/dev.jsonl">dev.jsonl</option>
              <option value="data/test.jsonl">test.jsonl</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="block text-xs font-medium text-muted mb-1">Limit (optional)</span>
            <input
              className="input w-28"
              placeholder="e.g. 10"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
            />
          </label>
          <button
            onClick={handleRun}
            disabled={running}
            className="bg-accent text-white font-medium px-4 py-2 rounded-md hover:opacity-90 disabled:opacity-40 transition-opacity"
          >
            {running ? "Running…" : "Run evaluation"}
          </button>
        </div>
        {runMessage && <p className="text-sm text-ink">{runMessage}</p>}
        <p className="text-xs text-muted">
          Running the full golden set makes one generation + one judge call per item (up to two
          judge calls if a retry is needed) — see the Cost panel on Judge Reliability for estimates.
        </p>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-ink mb-3">Categories &amp; scenarios</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {categories.map((c) => (
            <div key={c.id} className="bg-panel border border-line rounded-card shadow-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <span>{c.emoji}</span>
                <span className="text-sm font-medium text-ink">{c.label}</span>
                <span className="text-xs text-muted">({c.scenarios.length} scenarios)</span>
              </div>
              <ul className="text-sm text-muted space-y-1">
                {c.scenarios.map((s) => (
                  <li key={s.id}>· {s.label}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <style jsx global>{`
        .input {
          border: 1px solid #e4e4e0;
          border-radius: 8px;
          padding: 7px 10px;
          font-size: 0.875rem;
          background: white;
          color: #151a21;
        }
        .input:focus {
          outline: none;
          border-color: #3e5c8a;
        }
      `}</style>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-panel border border-line rounded-card shadow-card p-4">
      <div className="text-2xl font-semibold text-ink font-mono">{value}</div>
      <div className="text-xs text-muted mt-1">{label}</div>
    </div>
  );
}
