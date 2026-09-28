"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ResultRow } from "@/lib/api";
import { ScoreBadge, ScoreBar } from "@/components/ScoreBar";

const CATEGORY_OPTIONS = [
  { id: "", label: "All categories" },
  { id: "university", label: "University" },
  { id: "internship", label: "Internship & Jobs" },
  { id: "professional", label: "Professional" },
  { id: "customer_service", label: "Customer Service" },
];

export default function ResultsPage() {
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<ResultRow | null>(null);

  function load() {
    setLoading(true);
    api
      .listResults({
        category: category || undefined,
        min_score: minScore || undefined,
        status: statusFilter || undefined,
      })
      .then((d) => setRows(d.results))
      .finally(() => setLoading(false));
  }

  useEffect(load, [category, minScore, statusFilter]);

  const sorted = useMemo(
    () => [...rows].sort((a, b) => a.id.localeCompare(b.id)),
    [rows]
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Results</h1>
        <p className="text-muted mt-1">Every evaluated item from interactive use and harness runs.</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
          {CATEGORY_OPTIONS.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
        <select
          className="input"
          value={minScore}
          onChange={(e) => setMinScore(parseInt(e.target.value, 10))}
        >
          <option value={0}>Any score</option>
          <option value={9}>9-10 (pass, strict)</option>
          <option value={7}>7+ (pass)</option>
          <option value={5}>5+ </option>
        </select>
        <select className="input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="ok">Ok</option>
          <option value="generation_failed">Generation failed</option>
          <option value="judge_failed">Judge failed</option>
        </select>
        <span className="ml-auto self-center text-sm text-muted">{rows.length} items</span>
      </div>

      <div className="bg-panel border border-line rounded-card shadow-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-paper text-muted border-b border-line">
            <tr>
              {["ID", "Category", "Scenario", "Total", "Req.", "Acc.", "Tone", "Clar.", "Conc.", "Status"].map(
                (h) => (
                  <th key={h} className="text-left font-medium px-3 py-2">
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10} className="px-3 py-6 text-center text-muted">
                  Loading…
                </td>
              </tr>
            ) : sorted.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-3 py-6 text-center text-muted">
                  No results yet. Run an evaluation from the Dataset page, or evaluate an email on
                  the Evaluate page.
                </td>
              </tr>
            ) : (
              sorted.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r)}
                  className="border-b border-line last:border-0 hover:bg-paper cursor-pointer"
                >
                  <td className="px-3 py-2 font-mono text-xs">{r.id}</td>
                  <td className="px-3 py-2">{r.input.category}</td>
                  <td className="px-3 py-2 max-w-[200px] truncate">{r.input.scenario}</td>
                  <td className="px-3 py-2">
                    <ScoreBadge value={r.total_score} />
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{r.scores?.requirement_fulfillment ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.scores?.accuracy ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.scores?.tone ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.scores?.clarity ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.scores?.conciseness ?? "—"}</td>
                  <td className="px-3 py-2">
                    <StatusPill status={r.status} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selected && <DetailPanel row={selected} onClose={() => setSelected(null)} />}

      <style jsx global>{`
        .input {
          border: 1px solid #e4e4e0;
          border-radius: 8px;
          padding: 7px 10px;
          font-size: 0.875rem;
          background: white;
          color: #151a21;
        }
      `}</style>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    ok: "bg-good/10 text-good",
    generation_failed: "bg-bad/10 text-bad",
    judge_failed: "bg-bad/10 text-bad",
  };
  return (
    <span className={`px-2 py-0.5 rounded-md text-xs font-medium ${map[status] || "bg-line text-muted"}`}>
      {status}
    </span>
  );
}

function DetailPanel({ row, onClose }: { row: ResultRow; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-ink/40 flex items-start justify-center p-6 overflow-y-auto z-20" onClick={onClose}>
      <div
        className="bg-panel rounded-card shadow-card border border-line max-w-2xl w-full mt-10 p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink font-mono">{row.id}</h2>
          <button onClick={onClose} className="text-muted hover:text-ink text-sm">
            Close
          </button>
        </div>

        <div className="text-sm space-y-1">
          <p><span className="text-muted">Category:</span> {row.input.category}</p>
          <p><span className="text-muted">Scenario:</span> {row.input.scenario}</p>
          <p><span className="text-muted">Recipient:</span> {row.input.recipient}</p>
          <p><span className="text-muted">Context:</span> {row.input.context}</p>
        </div>

        {row.generated_email ? (
          <div className="border border-line rounded-md overflow-hidden">
            <div className="bg-paper px-4 py-2 border-b border-line text-xs text-muted">
              Subject: <span className="text-ink font-medium">{row.generated_email.subject}</span>
            </div>
            <div className="p-4 text-sm whitespace-pre-wrap leading-relaxed">
              {row.generated_email.greeting}
              {"\n\n"}
              {row.generated_email.body}
              {"\n\n"}
              {row.generated_email.closing}
            </div>
          </div>
        ) : (
          <p className="text-sm text-bad">Generation failed: {row.error}</p>
        )}

        {row.scores && (
          <div className="space-y-3">
            <div className="flex items-baseline justify-between">
              <h3 className="text-sm font-semibold text-ink">Score</h3>
              <span className="text-xl font-semibold text-ink font-mono">{row.total_score}/10</span>
            </div>
            <ScoreBar label="Requirement Fulfillment" value={row.scores.requirement_fulfillment} max={2} />
            <ScoreBar label="Accuracy" value={row.scores.accuracy} max={2} />
            <ScoreBar label="Tone" value={row.scores.tone} max={2} />
            <ScoreBar label="Clarity" value={row.scores.clarity} max={2} />
            <ScoreBar label="Conciseness" value={row.scores.conciseness} max={2} />
            <div>
              <div className="text-xs font-medium text-muted mb-1">Judge reasoning</div>
              <p className="text-sm">{row.reason}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
