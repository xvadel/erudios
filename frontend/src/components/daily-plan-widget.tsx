"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDailyPlan, type DailyPlan, type ReviewItem, type ConceptPerformance } from "@/lib/api";
import {
  Brain,
  Calendar,
  Clock,
  AlertTriangle,
  Target,
  Sparkles,
  ChevronRight,
  Flame,
  BookOpen,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

const DIFFICULTY_BADGE: Record<string, string> = {
  beginner: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25",
  intermediate: "bg-amber-500/15 text-amber-400 border border-amber-500/25",
  advanced: "bg-rose-500/15 text-rose-400 border border-rose-500/25",
};

function MasteryBar({ score }: { score: number }) {
  const color =
    score >= 80
      ? "bg-emerald-500"
      : score >= 50
      ? "bg-amber-500"
      : "bg-rose-500";
  return (
    <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
      <div
        className={cn("h-full rounded-full transition-all duration-700", color)}
        style={{ width: `${Math.min(score, 100)}%` }}
      />
    </div>
  );
}

function ReviewCard({ item }: { item: ReviewItem }) {
  const isOverdue = new Date(item.next_review) < new Date();
  return (
    <Link
      href={`/learn?topic=${item.topic_slug}`}
      className="group flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/5 hover:border-white/10 transition-all"
    >
      <div
        className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
          isOverdue
            ? "bg-rose-500/15 text-rose-400"
            : "bg-amber-500/15 text-amber-400"
        )}
      >
        <Calendar className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate">{item.topic_name}</p>
        <MasteryBar score={item.mastery_score} />
        <p className="text-xs text-white/40 mt-0.5">{item.mastery_score.toFixed(0)}% mastery</p>
      </div>
      <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-white/50 transition-colors flex-shrink-0" />
    </Link>
  );
}

function ConceptWeaknessCard({ concept }: { concept: ConceptPerformance }) {
  return (
    <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-rose-500/5 border border-rose-500/10">
      <AlertTriangle className="w-3.5 h-3.5 text-rose-400 mt-0.5 flex-shrink-0" />
      <div className="min-w-0">
        <p className="text-xs font-medium text-white truncate">{concept.concept_label.replace(/-/g, " ")}</p>
        <p className="text-xs text-white/40">{concept.accuracy_pct.toFixed(0)}% accuracy</p>
      </div>
    </div>
  );
}

export function DailyPlanWidget() {
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    getDailyPlan()
      .then(setPlan)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-5 animate-pulse">
        <div className="h-5 w-40 bg-white/10 rounded-md mb-4" />
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 bg-white/5 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !plan) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.02] overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-white/5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-violet-500/20 flex items-center justify-center">
              <Brain className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Today's Plan</h2>
              <p className="text-xs text-white/40">
                ~{plan.estimated_minutes} min estimated
              </p>
            </div>
          </div>
          {plan.review_items.length > 0 && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-rose-500/10 border border-rose-500/20">
              <Flame className="w-3 h-3 text-rose-400" />
              <span className="text-xs font-medium text-rose-400">
                {plan.review_items.length} due
              </span>
            </div>
          )}
        </div>

        {/* Daily Brief */}
        <p className="text-xs text-white/60 leading-relaxed italic border-l-2 border-violet-500/50 pl-3">
          {plan.brief}
        </p>
      </div>

      <div className="p-4 space-y-4">
        {/* Review Queue */}
        {plan.review_items.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-xs font-medium text-white/70 uppercase tracking-wider">
                Review Due
              </span>
            </div>
            <div className="space-y-1.5">
              {plan.review_items.map((item) => (
                <ReviewCard key={item.module_id} item={item} />
              ))}
            </div>
          </div>
        )}

        {/* New Topic Recommendations */}
        {plan.new_topics.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
              <span className="text-xs font-medium text-white/70 uppercase tracking-wider">
                Recommended
              </span>
            </div>
            <div className="space-y-1.5">
              {plan.new_topics.map((topic) => (
                <Link
                  key={topic.topic_slug}
                  href={`/explore?topic=${topic.topic_slug}`}
                  className="group flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/5 hover:border-violet-500/20 transition-all"
                >
                  <div className="w-8 h-8 rounded-lg bg-violet-500/15 flex items-center justify-center flex-shrink-0">
                    <BookOpen className="w-4 h-4 text-violet-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{topic.topic_name}</p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span
                        className={cn(
                          "text-xs px-1.5 py-0.5 rounded-full",
                          DIFFICULTY_BADGE[topic.difficulty] ?? DIFFICULTY_BADGE.beginner
                        )}
                      >
                        {topic.difficulty}
                      </span>
                      <span className="text-xs text-white/30">{topic.estimated_hours}h</span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-white/50 transition-colors flex-shrink-0" />
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Weak Concepts */}
        {plan.weak_concepts.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Target className="w-3.5 h-3.5 text-rose-400" />
              <span className="text-xs font-medium text-white/70 uppercase tracking-wider">
                Needs Work
              </span>
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              {plan.weak_concepts.map((c) => (
                <ConceptWeaknessCard key={`${c.concept_label}-${c.section_slug}`} concept={c} />
              ))}
            </div>
          </div>
        )}

        {plan.review_items.length === 0 && plan.new_topics.length === 0 && (
          <div className="text-center py-4">
            <TrendingUp className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm text-white/60">All caught up! Keep learning.</p>
          </div>
        )}
      </div>
    </div>
  );
}
