"use client";

import { useEffect, useState } from "react";
import { api, DashboardData } from "@/lib/api";

export default function ReliabilityPage() {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    api.getStatistics().then(setData).catch(() => {});
  }, []);

  if (!data) {
    return <p className="text-sm text-muted">Loading…</p>;
  }

  const perf = data.performance;
  const ha = data.human_agreement;
  const pb = data.position_bias;
  const vb = data.verbosity_bias;

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Judge Reliability &amp; Evaluation Dashboard</h1>
        <p className="text-muted mt-1">
          How much to trust the LLM judge — human agreement, position bias, verbosity bias — plus
          overall system performance and cost.
        </p>
      </div>

      {/* Human agreement */}
      <Section title="Human agreement">
        {ha?.human_vs_human ? (
          <div className="grid md:grid-cols-2 gap-4">
            <StatCard
              label="Overall exact agreement (both raters, all 5 criteria)"
              value={`${ha.human_vs_human.exact_full_agreement_pct}%`}
              sub={`${ha.human_vs_human.n_disagreements} disagreements / ${ha.human_vs_human.n_items} items`}
            />
            <div className="bg-panel border border-line rounded-card shadow-card p-4">
              <div className="text-xs font-medium text-muted mb-2">Agreement per criterion</div>
              <div className="space-y-1.5 text-sm">
                {Object.entries(ha.human_vs_human.agreement_per_criterion_pct as Record<string, number>).map(
                  ([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-ink capitalize">{k.replace(/_/g, " ")}</span>
                      <span className="font-mono text-muted">{v}%</span>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        ) : (
          <Empty text="Run `python data/human_labels/simulate_human_labels.py` (demo) or complete real labeling per data/LABELING_GUIDE.md, then `python -m harness.human_agreement`." />
        )}

        {ha?.judge_vs_human && (
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <StatCard
              label="Judge vs Human 1 agreement"
              value={`${ha.judge_vs_human.judge_vs_human1.exact_full_agreement_pct ?? "—"}%`}
            />
            <StatCard
              label="Judge vs Human 2 agreement"
              value={`${ha.judge_vs_human.judge_vs_human2.exact_full_agreement_pct ?? "—"}%`}
            />
          </div>
        )}
        {!ha?.judge_vs_human && (
          <p className="text-xs text-muted mt-2">
            Run a harness evaluation, then <code className="font-mono">python -m harness.human_agreement --results results/&lt;name&gt;.jsonl</code> to
            compare the judge against human labels (Experiment A).
          </p>
        )}
      </Section>

      {/* Position bias */}
      <Section title="Experiment B — Position bias">
        {pb ? (
          <div className="grid md:grid-cols-3 gap-4">
            <StatCard label="Pairs tested" value={pb.n_pairs_tested} />
            <StatCard label="Verdict flipped after swap" value={pb.n_flipped} />
            <StatCard label="Flip rate" value={`${pb.flip_rate_pct ?? "—"}%`} />
          </div>
        ) : (
          <Empty text="Run `python -m harness.position_bias --results results/<name>.jsonl` after a harness run to populate this." />
        )}
      </Section>

      {/* Verbosity bias */}
      <Section title="Experiment C — Verbosity bias">
        {vb ? (
          <div className="grid md:grid-cols-3 gap-4">
            <StatCard label="Items tested" value={vb.n_valid} />
            <StatCard label="Padding increased score" value={vb.n_padding_increased_score} />
            <StatCard label="% padding increased score" value={`${vb.pct_padding_increased_score ?? "—"}%`} />
          </div>
        ) : (
          <Empty text="Run `python -m harness.verbosity_bias --results results/<name>.jsonl` after a harness run to populate this." />
        )}
      </Section>

      {/* System performance */}
      <Section title="System performance">
        <div className="grid md:grid-cols-4 gap-4 mb-4">
          <StatCard label="Average score" value={perf.average_total_score ?? "—"} />
          <StatCard label="Evaluated items" value={perf.evaluated_items} />
          <StatCard label="Failed items" value={perf.failed_items} />
          <StatCard label="Total items" value={perf.total_items} />
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-panel border border-line rounded-card shadow-card p-4">
            <div className="text-xs font-medium text-muted mb-2">Average score by criterion</div>
            <div className="space-y-1.5 text-sm">
              {Object.entries(perf.average_by_criterion).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-ink capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="font-mono text-muted">{v}/2</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-panel border border-line rounded-card shadow-card p-4">
            <div className="text-xs font-medium text-muted mb-2">Average score by category</div>
            <div className="space-y-1.5 text-sm">
              {Object.entries(perf.average_by_category).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-ink capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="font-mono text-muted">{v}/10</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* Cost */}
      <Section title="Cost">
        <div className="grid md:grid-cols-4 gap-4">
          <StatCard label="Total API cost" value={`$${perf.cost.total_cost_usd.toFixed(4)}`} />
          <StatCard
            label="Cost per evaluated email"
            value={perf.cost.cost_per_item_usd !== null ? `$${perf.cost.cost_per_item_usd.toFixed(5)}` : "—"}
          />
          <StatCard
            label="Estimated cost per 1,000"
            value={perf.cost.estimated_cost_per_1000 !== null ? `$${perf.cost.estimated_cost_per_1000.toFixed(2)}` : "—"}
          />
          <StatCard
            label="Estimated cost at 100× scale"
            value={perf.cost.estimated_cost_at_100x !== null ? `$${perf.cost.estimated_cost_at_100x.toFixed(2)}` : "—"}
          />
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-sm font-semibold text-ink mb-3">{title}</h2>
      {children}
    </section>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-panel border border-line rounded-card shadow-card p-4">
      <div className="text-xl font-semibold text-ink font-mono">{value}</div>
      <div className="text-xs text-muted mt-1">{label}</div>
      {sub && <div className="text-xs text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="text-sm text-muted border border-dashed border-line rounded-card p-4">
      {text}
    </div>
  );
}
