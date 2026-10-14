"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getRootTopics, type Topic } from "@/lib/api";
import { Brain, ChevronRight, Clock, BarChart2 } from "lucide-react";
import { cn } from "@/lib/utils";

const DOMAIN_ICONS: Record<string, string> = {
  "machine-learning": "🤖",
  "deep-learning": "🧠",
  "natural-language-processing": "💬",
  "computer-vision": "👁️",
  "reinforcement-learning": "🎮",
  mlops: "⚙️",
  "agentic-ai": "🕹️",
  "artificial-intelligence": "✨",
};

const DOMAIN_GRADIENT: Record<string, string> = {
  "machine-learning": "from-blue-600/20 to-blue-800/5 hover:border-blue-500/40",
  "deep-learning": "from-violet-600/20 to-violet-800/5 hover:border-violet-500/40",
  "natural-language-processing": "from-emerald-600/20 to-emerald-800/5 hover:border-emerald-500/40",
  "computer-vision": "from-orange-600/20 to-orange-800/5 hover:border-orange-500/40",
  "reinforcement-learning": "from-red-600/20 to-red-800/5 hover:border-red-500/40",
  mlops: "from-slate-600/20 to-slate-800/5 hover:border-slate-500/40",
  "agentic-ai": "from-cyan-600/20 to-cyan-800/5 hover:border-cyan-500/40",
  "artificial-intelligence": "from-indigo-600/20 to-indigo-800/5 hover:border-indigo-500/40",
};

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  return (
    <span
      className={cn(
        "text-xs px-2 py-0.5 rounded-full font-medium",
        difficulty === "beginner" && "badge-beginner",
        difficulty === "intermediate" && "badge-intermediate",
        difficulty === "advanced" && "badge-advanced"
      )}
    >
      {difficulty}
    </span>
  );
}

function TopicCard({ topic, index }: { topic: Topic; index: number }) {
  const icon = DOMAIN_ICONS[topic.slug] || "📚";
  const gradient =
    DOMAIN_GRADIENT[topic.slug] ||
    "from-indigo-600/15 to-indigo-800/5 hover:border-indigo-500/40";

  return (
    <Link
      href={`/explore/${topic.slug}`}
      className={cn(
        "group relative rounded-2xl bg-gradient-to-br border border-white/8 p-6",
        "transition-all duration-300 hover:-translate-y-1.5 hover:shadow-xl",
        "animate-fade-in-up",
        gradient
      )}
      style={{ animationDelay: `${index * 0.06}s`, opacity: 0 }}
    >
      <div className="flex items-start justify-between mb-4">
        <span className="text-3xl">{icon}</span>
        <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 transition-all duration-150" />
      </div>

      <h3 className="font-semibold text-foreground mb-1.5 group-hover:text-white transition-colors">
        {topic.name}
      </h3>

      {topic.description && (
        <p className="text-xs text-muted-foreground line-clamp-2 mb-4 leading-relaxed">
          {topic.description}
        </p>
      )}

      <div className="flex items-center justify-between">
        <DifficultyBadge difficulty={topic.difficulty} />
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="w-3 h-3" />
          {topic.estimated_hours}h
        </div>
      </div>

      {topic.child_count > 0 && (
        <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-1 text-xs text-muted-foreground">
          <BarChart2 className="w-3 h-3" />
          {topic.child_count} sub-topics
        </div>
      )}
    </Link>
  );
}

function TopicCardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/8 p-6 space-y-4">
      <div className="shimmer h-8 w-8 rounded-lg" />
      <div className="space-y-2">
        <div className="shimmer h-4 w-2/3 rounded" />
        <div className="shimmer h-3 w-full rounded" />
        <div className="shimmer h-3 w-4/5 rounded" />
      </div>
      <div className="flex justify-between">
        <div className="shimmer h-5 w-20 rounded-full" />
        <div className="shimmer h-4 w-12 rounded" />
      </div>
    </div>
  );
}

export function TopicGrid() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRootTopics()
      .then(setTopics)
      .catch(() => setError("Could not load topics. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="py-20 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-10">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-1">
              AI & ML Domains
            </h2>
            <p className="text-muted-foreground text-sm">
              Choose a domain to explore its learning path
            </p>
          </div>
          <Link
            href="/explore"
            className="hidden sm:flex items-center gap-1.5 text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            View all
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>

        {error && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-6 py-4 text-rose-400 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {loading
            ? Array.from({ length: 8 }).map((_, i) => <TopicCardSkeleton key={i} />)
            : topics
                .filter((t) => t.slug !== "artificial-intelligence")
                .map((topic, i) => (
                  <TopicCard key={topic.id} topic={topic} index={i} />
                ))}
        </div>
      </div>
    </section>
  );
}
