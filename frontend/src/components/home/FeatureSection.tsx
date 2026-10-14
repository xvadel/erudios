"use client";

import { Map, Zap, Shield, RefreshCw, BarChart3, BookMarked } from "lucide-react";

const FEATURES = [
  {
    icon: Map,
    title: "Clear Learning Paths",
    description:
      'Pre-built dependency graphs answer "what should I learn next?" instantly — no guesswork, no random jumping between topics.',
    color: "indigo",
  },
  {
    icon: BookMarked,
    title: "Curated Resources",
    description:
      "Automatically discovers and ranks blogs, papers, GitHub repos, courses, and videos — filtered by trust score and freshness.",
    color: "cyan",
  },
  {
    icon: Zap,
    title: "Lazy Generation",
    description:
      "Content generated section-by-section only when you need it. Cached and shared — fast, efficient, and zero token waste.",
    color: "violet",
  },
  {
    icon: Shield,
    title: "Trusted Sources Only",
    description:
      "Resources scored on authority, recency, and community signals. ArXiv, official docs, and top AI researchers first.",
    color: "emerald",
  },
  {
    icon: RefreshCw,
    title: "Always Up to Date",
    description:
      "Weekly refresh pipeline re-checks every resource, flags stale links, and discovers new content automatically.",
    color: "amber",
  },
  {
    icon: BarChart3,
    title: "Track Your Progress",
    description:
      "Quiz-based mastery scoring, spaced repetition scheduling, and gap detection tells you exactly where to focus.",
    color: "rose",
  },
];

const COLOR_MAP: Record<string, string> = {
  indigo: "from-indigo-500/20 to-indigo-600/5 border-indigo-500/20 group-hover:border-indigo-500/40",
  cyan: "from-cyan-500/20 to-cyan-600/5 border-cyan-500/20 group-hover:border-cyan-500/40",
  violet: "from-violet-500/20 to-violet-600/5 border-violet-500/20 group-hover:border-violet-500/40",
  emerald: "from-emerald-500/20 to-emerald-600/5 border-emerald-500/20 group-hover:border-emerald-500/40",
  amber: "from-amber-500/20 to-amber-600/5 border-amber-500/20 group-hover:border-amber-500/40",
  rose: "from-rose-500/20 to-rose-600/5 border-rose-500/20 group-hover:border-rose-500/40",
};

const ICON_COLOR: Record<string, string> = {
  indigo: "text-indigo-400",
  cyan: "text-cyan-400",
  violet: "text-violet-400",
  emerald: "text-emerald-400",
  amber: "text-amber-400",
  rose: "text-rose-400",
};

export function FeatureSection() {
  return (
    <section className="py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            Built for serious learners
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Every feature is designed around one goal: getting you from{" "}
            <em className="text-foreground/80 not-italic">scattered confusion</em> to{" "}
            <em className="text-foreground/80 not-italic">structured mastery</em>.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f, i) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className={`group relative rounded-2xl bg-gradient-to-br ${COLOR_MAP[f.color]} border p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg animate-fade-in-up`}
                style={{ animationDelay: `${i * 0.07}s`, opacity: 0 }}
              >
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 mb-4 ${ICON_COLOR[f.color]}`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-foreground mb-2">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
