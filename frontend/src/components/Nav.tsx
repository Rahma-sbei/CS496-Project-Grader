"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Evaluate" },
  { href: "/dataset", label: "Dataset" },
  { href: "/results", label: "Results" },
  { href: "/reliability", label: "Judge Reliability" },
  { href: "/prompts", label: "Prompt Versions" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="border-b border-line bg-paper/95 backdrop-blur sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-6 flex items-center h-14 gap-8">
        <span className="font-semibold text-ink tracking-tight">Email Grader</span>
        <nav className="flex gap-1 text-sm">
          {LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3 py-1.5 rounded-md transition-colors ${
                  active
                    ? "bg-accentSoft text-accent font-medium"
                    : "text-muted hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
