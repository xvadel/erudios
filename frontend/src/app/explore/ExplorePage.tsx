"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search, X, ChevronRight, Clock, BarChart2 } from "lucide-react";
import Link from "next/link";
import { getRootTopics, searchTopics, type Topic } from "@/lib/api";
import { cn } from "@/lib/utils";

const DIFFICULTIES = ["beginner", "intermediate", "advanced"];

export default function ExplorePage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const q = searchParams.get("q") || "";

  const [query, setQuery] = useState(q);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [difficulty, setDifficulty] = useState<string | null>(null);

  const load = useCallback(async (search: string) => {
    setLoading(true);
    try {
      const data = search.trim()
        ? await searchTopics(search)
        : await getRootTopics();
      setTopics(data.filter((t) => t.slug !== "artificial-intelligence"));
    } catch {
      setTopics([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(q);
    setQuery(q);
  }, [q, load]);

  const handleSearch = () => {
    if (query.trim()) {
      router.push(`/explore?q=${encodeURIComponent(query.trim())}`);
    } else {
      router.push("/explore");
    }
  };

  const filtered = difficulty
    ? topics.filter((t) => t.difficulty === difficulty)
    : topics;

  return (
    <div className="max-w-7xl mx-auto px-4 pt-24 pb-20">
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2">
          {q ? (
            <>
              Results for{" "}
              <span className="gradient-text">"{q}"</span>
            </>
          ) : (
            "Explore AI & ML Topics"
          )}
        </h1>
        <p className="text-muted-foreground">
          {loading ? "Loading…" : `${filtered.length} topic${filtered.length !== 1 ? "s" : ""} found`}
        </p>
      </div>

      {/* Search + filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-8">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search topics…"
            className="w-full h-11 pl-10 pr-4 rounded-xl bg-white/5 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-indigo-500/50 transition-all"
          />
        </div>

        <div className="flex gap-2 flex-wrap">
          {DIFFICULTIES.map((d) => (
            <button
              key={d}
              onClick={() => setDifficulty(difficulty === d ? null : d)}
              className={cn(
                "px-3 py-2 rounded-xl text-sm border transition-all duration-150",
                difficulty === d
                  ? "border-indigo-500/60 bg-indigo-500/15 text-indigo-300"
                  : "border-white/10 bg-white/5 text-muted-foreground hover:text-foreground hover:border-white/20"
              )}
            >
              {d.charAt(0).toUpperCase() + d.slice(1)}
            </button>
          ))}
          {difficulty && (
            <button
              onClick={() => setDifficulty(null)}
              className="p-2 rounded-xl border border-white/10 bg-white/5 text-muted-foreground hover:text-foreground transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="rounded-2xl border border-white/8 p-5 space-y-3">
              <div className="shimmer h-5 w-3/4 rounded" />
              <div className="shimmer h-3 w-full rounded" />
              <div className="shimmer h-3 w-2/3 rounded" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <Search className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p>No topics found. Try a different search term.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((topic, i) => (
            <Link
              key={topic.id}
              href={`/explore/${topic.slug}`}
              className="group glass-hover rounded-2xl p-5 animate-fade-in-up"
              style={{ animationDelay: `${i * 0.04}s`, opacity: 0 }}
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-foreground group-hover:text-white transition-colors">
                  {topic.name}
                </h3>
                <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5 group-hover:translate-x-0.5 transition-transform" />
              </div>

              {topic.description && (
                <p className="text-sm text-muted-foreground line-clamp-2 mb-4 leading-relaxed">
                  {topic.description}
                </p>
              )}

              <div className="flex items-center justify-between">
                <span
                  className={cn(
                    "text-xs px-2 py-0.5 rounded-full font-medium",
                    topic.difficulty === "beginner" && "badge-beginner",
                    topic.difficulty === "intermediate" && "badge-intermediate",
                    topic.difficulty === "advanced" && "badge-advanced"
                  )}
                >
                  {topic.difficulty}
                </span>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  {topic.child_count > 0 && (
                    <span className="flex items-center gap-1">
                      <BarChart2 className="w-3 h-3" />
                      {topic.child_count}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {topic.estimated_hours}h
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
