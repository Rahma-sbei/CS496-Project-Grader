const COLOR_BY_RATIO = (ratio: number) => {
  if (ratio >= 0.85) return "bg-good";
  if (ratio >= 0.5) return "bg-warn";
  return "bg-bad";
};

export function ScoreBar({
  label,
  value,
  max,
}: {
  label: string;
  value: number;
  max: number;
}) {
  const ratio = max > 0 ? value / max : 0;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-ink">{label}</span>
        <span className="text-muted font-mono">
          {value}/{max}
        </span>
      </div>
      <div className="h-2 rounded-full bg-line overflow-hidden">
        <div
          className={`h-full rounded-full ${COLOR_BY_RATIO(ratio)}`}
          style={{ width: `${ratio * 100}%` }}
        />
      </div>
    </div>
  );
}

export function ScoreBadge({ value, max = 10 }: { value: number | null; max?: number }) {
  if (value === null) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-line text-muted">
        —
      </span>
    );
  }
  const ratio = value / max;
  const color =
    ratio >= 0.85
      ? "bg-good/10 text-good"
      : ratio >= 0.5
      ? "bg-warn/10 text-warn"
      : "bg-bad/10 text-bad";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono font-semibold ${color}`}>
      {value}/{max}
    </span>
  );
}
