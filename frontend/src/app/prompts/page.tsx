"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function PromptsPage() {
  const [versions, setVersions] = useState<string[]>([]);
  const [changelog, setChangelog] = useState("");

  useEffect(() => {
    api.getPromptVersions().then((d) => {
      setVersions(d.versions);
      setChangelog(d.changelog);
    });
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Prompt Versions</h1>
        <p className="text-muted mt-1">
          Every prompt change is versioned as a new file under <code className="font-mono text-xs">prompts/</code> and
          tracked here with the measured effect on dev/test scores.
        </p>
      </div>

      <div className="flex gap-2">
        {versions.map((v) => (
          <span key={v} className="px-2.5 py-1 rounded-md bg-accentSoft text-accent text-sm font-mono">
            {v}
          </span>
        ))}
        {versions.length === 0 && <p className="text-sm text-muted">No prompt versions found.</p>}
      </div>

      <div className="bg-panel border border-line rounded-card shadow-card p-6">
        <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed text-ink">{changelog}</pre>
      </div>
    </div>
  );
}
