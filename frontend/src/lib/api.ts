// Thin client for the FastAPI backend. Next.js rewrites /api/* to the
// backend (see next.config.js), so relative fetches work in both dev and
// production without ever putting an API key or backend URL in the browser.

export type Scenario = {
  id: string;
  label: string;
  recipient: string;
  purpose: string;
  required_information: string[];
};

export type Category = {
  id: string;
  label: string;
  emoji: string;
  scenarios: Scenario[];
};

export type GeneratedEmail = {
  subject: string;
  greeting: string;
  body: string;
  closing: string;
};

export type Usage = {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  model: string;
  prompt_version: string;
} | null;

export type JudgeScores = {
  requirement_fulfillment: number;
  accuracy: number;
  tone: number;
  clarity: number;
  conciseness: number;
  total_score: number;
  reason: string;
};

export type EvalInput = {
  category: string;
  scenario: string;
  recipient: string;
  purpose: string;
  context: string;
  required_information: string[];
  tone: string;
  max_length: string;
};

export type ResultRow = {
  id: string;
  input: EvalInput;
  generated_email: GeneratedEmail | null;
  scores: JudgeScores | null;
  total_score: number | null;
  reason: string | null;
  status: string;
  error: string | null;
  generation_usage: Usage;
  judge_usage: Usage;
  timestamp: string;
};

export type Statistics = {
  total_items: number;
  evaluated_items: number;
  failed_items: number;
  failed_ids: string[];
  average_total_score: number | null;
  score_distribution: Record<string, number>;
  average_by_criterion: Record<string, number>;
  average_by_category: Record<string, number>;
  cost: {
    total_cost_usd: number;
    cost_per_item_usd: number | null;
    estimated_cost_per_1000: number | null;
    estimated_cost_at_100x: number | null;
  };
};

export type DashboardData = {
  dataset: Record<string, number>;
  performance: Statistics;
  human_agreement: any;
  position_bias: any;
  verbosity_bias: any;
};

async function jsonFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  getCategories: () => jsonFetch<{ categories: Category[] }>("/api/categories"),

  generateEmail: (payload: EvalInput) =>
    jsonFetch<{ email: GeneratedEmail; usage: Usage }>("/api/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  evaluateEmail: (scenario: EvalInput, generated_email: GeneratedEmail) =>
    jsonFetch<ResultRow>("/api/evaluate", {
      method: "POST",
      body: JSON.stringify({ scenario, generated_email }),
    }),

  runEvaluation: (payload: {
    dataset?: string;
    output_name?: string;
    limit?: number;
  }) =>
    jsonFetch<{ output_name: string; statistics: Statistics; n_results: number }>(
      "/api/run-evaluation",
      { method: "POST", body: JSON.stringify(payload) }
    ),

  listResults: (params?: { category?: string; min_score?: number; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.min_score !== undefined) qs.set("min_score", String(params.min_score));
    if (params?.status) qs.set("status", params.status);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return jsonFetch<{ results: ResultRow[]; count: number }>(`/api/results${suffix}`);
  },

  getResult: (id: string) => jsonFetch<ResultRow>(`/api/results/${id}`),

  getStatistics: () => jsonFetch<DashboardData>("/api/statistics"),

  getPromptVersions: () =>
    jsonFetch<{ versions: string[]; changelog: string }>("/api/prompt-versions"),
};
