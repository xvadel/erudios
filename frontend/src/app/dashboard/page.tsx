"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  listMyCurricula,
  deleteCurriculum,
  type CurriculumSummary,
} from "@/lib/api";
import {
  BookOpen,
  Brain,
  ChevronRight,
  Clock,
  GraduationCap,
  Plus,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  intermediate: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  advanced: "text-rose-400 bg-rose-400/10 border-rose-400/20",
};

const LEVEL_LABELS: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

const STYLE_LABELS: Record<string, string> = {
  visual: "Visual",
  practical: "Hands-on",
  research: "Research",
  interview: "Interview Prep",
  project: "Project-based",
};

const GOAL_LABELS: Record<string, string> = {
  job: "Get a Job",
  research: "Research",
  startup: "Build a Startup",
  academic: "Academic Study",
  general: "General",
};

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const [curricula, setCurricula] = useState<CurriculumSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/auth/login");
      return;
    }
    listMyCurricula()
      .then(setCurricula)
      .catch(() => toast({ title: "Failed to load your curricula", variant: "destructive" }))
      .finally(() => setLoading(false));
  }, [user, authLoading, router, toast]);

  const handleDelete = async (id: string, name: string) => {
    setDeletingId(id);
    try {
      await deleteCurriculum(id);
      setCurricula((prev) => prev.filter((c) => c.id !== id));
      toast({ title: `Removed curriculum for "${name}"` });
    } catch {
      toast({ title: "Failed to delete curriculum", variant: "destructive" });
    } finally {
      setDeletingId(null);
    }
  };

  if (authLoading || loading) {
    return <DashboardSkeleton />;
  }

  const totalModules = curricula.reduce((s, c) => s + c.module_count, 0);

  return (
    <div className="max-w-5xl mx-auto px-4 pt-24 pb-20">
      {/* Header */}
      <div className="mb-10 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1">
            My Learning Hub
          </h1>
          <p className="text-muted-foreground">
            {curricula.length === 0
              ? "Start your first curriculum to begin learning."
              : `${curricula.length} curriculum${curricula.length !== 1 ? "s" : ""} · ${totalModules} total modules`}
          </p>
        </div>
        <Link href="/explore">
          <Button
            id="dashboard-explore-btn"
            className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-500/20"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Curriculum
          </Button>
        </Link>
      </div>

      {/* Stats bar */}
      {curricula.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-10">
          {[
            {
              icon: BookOpen,
              label: "Curricula",
              value: curricula.length,
              color: "text-indigo-400",
            },
            {
              icon: Brain,
              label: "Total Modules",
              value: totalModules,
              color: "text-violet-400",
            },
            {
              icon: TrendingUp,
              label: "Topics Covered",
              value: new Set(curricula.map((c) => c.topic_slug)).size,
              color: "text-emerald-400",
            },
            {
              icon: Target,
              label: "Learning Goals",
              value: new Set(curricula.map((c) => c.goal)).size,
              color: "text-amber-400",
            },
          ].map(({ icon: Icon, label, value, color }) => (
            <div key={label} className="glass rounded-xl p-4 text-center">
              <Icon className={cn("w-5 h-5 mx-auto mb-2", color)} />
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Curricula grid */}
      {curricula.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {curricula.map((c) => (
            <CurriculumCard
              key={c.id}
              curriculum={c}
              onDelete={handleDelete}
              isDeleting={deletingId === c.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function CurriculumCard({
  curriculum,
  onDelete,
  isDeleting,
}: {
  curriculum: CurriculumSummary;
  onDelete: (id: string, name: string) => void;
  isDeleting: boolean;
}) {
  const createdAt = new Date(curriculum.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="glass-hover rounded-2xl p-5 group flex flex-col gap-4">
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold text-base leading-tight mb-1 line-clamp-1">
            {curriculum.topic_name}
          </h2>
          <div className="flex flex-wrap gap-1.5">
            <span
              className={cn(
                "text-xs px-2 py-0.5 rounded-full border font-medium",
                DIFFICULTY_COLORS[curriculum.level] ?? "text-muted-foreground bg-white/5 border-white/10"
              )}
            >
              {LEVEL_LABELS[curriculum.level] ?? curriculum.level}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-muted-foreground">
              {STYLE_LABELS[curriculum.learning_style] ?? curriculum.learning_style}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-muted-foreground">
              {GOAL_LABELS[curriculum.goal] ?? curriculum.goal}
            </span>
          </div>
        </div>
        <button
          id={`delete-curriculum-${curriculum.id}`}
          onClick={() => onDelete(curriculum.id, curriculum.topic_name)}
          disabled={isDeleting}
          className="shrink-0 p-1.5 rounded-lg text-muted-foreground hover:text-rose-400 hover:bg-rose-400/10 transition-all opacity-0 group-hover:opacity-100 disabled:opacity-50"
          aria-label="Delete curriculum"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Module count + date */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <GraduationCap className="w-3.5 h-3.5" />
          {curriculum.module_count} modules
        </span>
        <span className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          {createdAt}
        </span>
      </div>

      {/* CTA */}
      <Link
        href={`/learn/${curriculum.topic_slug}`}
        id={`continue-curriculum-${curriculum.id}`}
        className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-indigo-600/15 border border-indigo-500/20 text-indigo-400 text-sm font-medium hover:bg-indigo-600/25 hover:border-indigo-500/40 transition-all group/btn"
      >
        <Sparkles className="w-3.5 h-3.5" />
        Continue Learning
        <ChevronRight className="w-3.5 h-3.5 group-hover/btn:translate-x-0.5 transition-transform" />
      </Link>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-20 space-y-5">
      <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
        <Brain className="w-8 h-8 text-indigo-400" />
      </div>
      <div>
        <h3 className="text-lg font-semibold mb-2">No curricula yet</h3>
        <p className="text-muted-foreground text-sm max-w-sm mx-auto">
          Explore topics and click <strong>Build My Curriculum</strong> to get
          a personalized, AI-generated learning path.
        </p>
      </div>
      <Link href="/explore">
        <Button
          id="empty-state-explore-btn"
          className="bg-indigo-600 hover:bg-indigo-500 text-white"
        >
          <Plus className="w-4 h-4 mr-2" />
          Explore Topics
        </Button>
      </Link>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="max-w-5xl mx-auto px-4 pt-24 pb-20 space-y-8">
      <div className="space-y-2">
        <div className="shimmer h-9 w-56 rounded-lg" />
        <div className="shimmer h-4 w-40 rounded" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="shimmer h-24 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="shimmer h-44 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}
