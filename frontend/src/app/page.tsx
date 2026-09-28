"use client";

import { useEffect, useState } from "react";
import { api, Category, Scenario, GeneratedEmail, ResultRow, EvalInput } from "@/lib/api";
import { ScoreBar } from "@/components/ScoreBar";

type Step = "category" | "scenario" | "configure" | "result";

export default function EvaluatePage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(true);
  const [step, setStep] = useState<Step>("category");

  const [category, setCategory] = useState<Category | null>(null);
  const [scenario, setScenario] = useState<Scenario | null>(null);

  const [config, setConfig] = useState<EvalInput | null>(null);
  const [requiredInfoText, setRequiredInfoText] = useState("");

  const [email, setEmail] = useState<GeneratedEmail | null>(null);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  const [result, setResult] = useState<ResultRow | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getCategories()
      .then((d) => setCategories(d.categories))
      .catch(() => setCategories([]))
      .finally(() => setLoadingCategories(false));
  }, []);

  function pickCategory(c: Category) {
    setCategory(c);
    setStep("scenario");
  }

  function pickScenario(s: Scenario) {
    setScenario(s);
    setRequiredInfoText(s.required_information.join("\n"));
    setConfig({
      category: category!.id,
      scenario: s.label,
      recipient: s.recipient,
      purpose: s.purpose,
      context: "",
      required_information: s.required_information,
      tone: "Professional and respectful",
      max_length: "Short (under 120 words)",
    });
    setStep("configure");
  }

  async function handleGenerate() {
    if (!config) return;
    setGenerating(true);
    setGenError(null);
    setEmail(null);
    setResult(null);
    try {
      const payload = {
        ...config,
        required_information: requiredInfoText.split("\n").map((s) => s.trim()).filter(Boolean),
      };
      setConfig(payload);
      const res = await api.generateEmail(payload);
      setEmail(res.email);
      setStep("result");
    } catch (e: any) {
      setGenError(e.message || "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function handleEvaluate() {
    if (!config || !email) return;
    setEvaluating(true);
    setEvalError(null);
    try {
      const res = await api.evaluateEmail(config, email);
      setResult(res);
    } catch (e: any) {
      setEvalError(e.message || "Evaluation failed");
    } finally {
      setEvaluating(false);
    }
  }

  function startOver() {
    setCategory(null);
    setScenario(null);
    setConfig(null);
    setEmail(null);
    setResult(null);
    setStep("category");
  }

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Email Grader</h1>
        <p className="text-muted mt-1 max-w-2xl">
          Evaluate the quality of AI-generated emails with a reproducible LLM evaluation harness.
        </p>
      </div>

      {/* Step: category */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-ink">Choose an email category</h2>
          {category && (
            <button onClick={startOver} className="text-xs text-accent hover:underline">
              Start over
            </button>
          )}
        </div>
        {loadingCategories ? (
          <p className="text-sm text-muted">Loading categories…</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {categories.map((c) => (
              <button
                key={c.id}
                onClick={() => pickCategory(c)}
                className={`text-left p-4 rounded-card border transition-colors bg-panel shadow-card ${
                  category?.id === c.id ? "border-accent ring-1 ring-accent" : "border-line hover:border-accent/50"
                }`}
              >
                <div className="text-2xl mb-2">{c.emoji}</div>
                <div className="text-sm font-medium text-ink">{c.label}</div>
                <div className="text-xs text-muted mt-1">{c.scenarios.length} scenarios</div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Step: scenario */}
      {category && (
        <section>
          <h2 className="text-sm font-semibold text-ink mb-3">
            Choose a scenario in {category.label}
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {category.scenarios.map((s) => (
              <button
                key={s.id}
                onClick={() => pickScenario(s)}
                className={`text-left px-3 py-2.5 rounded-md border text-sm bg-panel transition-colors ${
                  scenario?.id === s.id
                    ? "border-accent ring-1 ring-accent text-accent"
                    : "border-line hover:border-accent/50 text-ink"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Step: configure */}
      {config && scenario && (
        <section className="grid md:grid-cols-2 gap-6">
          <div className="bg-panel border border-line rounded-card shadow-card p-5 space-y-4">
            <h2 className="text-sm font-semibold text-ink">Scenario configuration</h2>

            <Field label="Recipient">
              <input
                className="input"
                value={config.recipient}
                onChange={(e) => setConfig({ ...config, recipient: e.target.value })}
              />
            </Field>
            <Field label="Purpose">
              <input
                className="input"
                value={config.purpose}
                onChange={(e) => setConfig({ ...config, purpose: e.target.value })}
              />
            </Field>
            <Field label="Context">
              <textarea
                className="input min-h-[72px]"
                placeholder="What's the situation? e.g. My laptop stopped working and I could not finish the assignment."
                value={config.context}
                onChange={(e) => setConfig({ ...config, context: e.target.value })}
              />
            </Field>
            <Field label="Required information (one per line)">
              <textarea
                className="input min-h-[96px] font-mono text-xs"
                value={requiredInfoText}
                onChange={(e) => setRequiredInfoText(e.target.value)}
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Desired tone">
                <input
                  className="input"
                  value={config.tone}
                  onChange={(e) => setConfig({ ...config, tone: e.target.value })}
                />
              </Field>
              <Field label="Maximum length">
                <input
                  className="input"
                  value={config.max_length}
                  onChange={(e) => setConfig({ ...config, max_length: e.target.value })}
                />
              </Field>
            </div>

            <button
              onClick={handleGenerate}
              disabled={generating || !config.context.trim()}
              className="w-full mt-2 bg-accent text-white font-medium py-2.5 rounded-md hover:opacity-90 disabled:opacity-40 transition-opacity"
            >
              {generating ? "Generating…" : "Generate Email"}
            </button>
            {!config.context.trim() && (
              <p className="text-xs text-muted">Add context above to enable generation.</p>
            )}
            {genError && <p className="text-xs text-bad">{genError}</p>}
          </div>

          {/* Email preview + evaluation */}
          <div className="space-y-4">
            {email ? (
              <>
                <div className="bg-panel border border-line rounded-card shadow-card overflow-hidden">
                  <div className="border-b border-line px-5 py-3 bg-paper">
                    <div className="text-xs text-muted">Subject</div>
                    <div className="text-sm font-medium text-ink">{email.subject}</div>
                  </div>
                  <div className="p-5 text-sm text-ink whitespace-pre-wrap leading-relaxed">
                    {email.greeting}
                    {"\n\n"}
                    {email.body}
                    {"\n\n"}
                    {email.closing}
                  </div>
                </div>

                <button
                  onClick={handleEvaluate}
                  disabled={evaluating}
                  className="w-full bg-ink text-white font-medium py-2.5 rounded-md hover:opacity-90 disabled:opacity-40 transition-opacity"
                >
                  {evaluating ? "Evaluating…" : "Evaluate Email"}
                </button>
                {evalError && <p className="text-xs text-bad">{evalError}</p>}

                {result && result.scores && (
                  <div className="bg-panel border border-line rounded-card shadow-card p-5 space-y-4">
                    <div className="flex items-baseline justify-between">
                      <h3 className="text-sm font-semibold text-ink">Overall Score</h3>
                      <span className="text-2xl font-semibold text-ink font-mono">
                        {result.total_score} / 10
                      </span>
                    </div>
                    <div className="space-y-3">
                      <ScoreBar label="Requirement Fulfillment" value={result.scores.requirement_fulfillment} max={2} />
                      <ScoreBar label="Accuracy" value={result.scores.accuracy} max={2} />
                      <ScoreBar label="Tone" value={result.scores.tone} max={2} />
                      <ScoreBar label="Clarity" value={result.scores.clarity} max={2} />
                      <ScoreBar label="Conciseness" value={result.scores.conciseness} max={2} />
                    </div>
                    <div>
                      <div className="text-xs font-medium text-muted mb-1">Judge reasoning</div>
                      <p className="text-sm text-ink leading-relaxed">{result.reason}</p>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="h-full min-h-[200px] flex items-center justify-center text-sm text-muted border border-dashed border-line rounded-card">
                Generate an email to see the preview here
              </div>
            )}
          </div>
        </section>
      )}

      <style jsx global>{`
        .input {
          width: 100%;
          border: 1px solid #e4e4e0;
          border-radius: 8px;
          padding: 8px 10px;
          font-size: 0.875rem;
          background: white;
          color: #151a21;
        }
        .input:focus {
          outline: none;
          border-color: #3e5c8a;
          box-shadow: 0 0 0 2px #eaeff7;
        }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-muted mb-1">{label}</span>
      {children}
    </label>
  );
}
