"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getUserBookmarks, type ResourceOut } from "@/lib/api";
import { ResourceFeedbackActions } from "@/components/resource-feedback-actions";
import { Bookmark, ExternalLink, BookOpen, StickyNote, FileText, Github } from "lucide-react";
import { cn } from "@/lib/utils";

const SOURCE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  blog: BookOpen,
  paper: FileText,
  github: Github,
  video: StickyNote,
};

const SOURCE_COLORS: Record<string, string> = {
  blog: "text-sky-400 bg-sky-500/10",
  paper: "text-violet-400 bg-violet-500/10",
  github: "text-emerald-400 bg-emerald-500/10",
  video: "text-rose-400 bg-rose-500/10",
};

function ResourceCard({ resource }: { resource: ResourceOut }) {
  const [item, setItem] = useState(resource);
  const SourceIcon = SOURCE_ICONS[item.source_type] ?? BookOpen;
  const sourceColor = SOURCE_COLORS[item.source_type] ?? "text-white/50 bg-white/5";

  if (!item.user_feedback?.bookmarked) return null;

  return (
    <div className="group rounded-2xl border border-white/8 bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/12 transition-all p-4">
      <div className="flex items-start gap-3">
        {/* Source Icon */}
        <div
          className={cn(
            "w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0",
            sourceColor
          )}
        >
          <SourceIcon className="w-4 h-4" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-white hover:text-violet-300 transition-colors line-clamp-2 leading-snug"
              >
                {item.title}
              </a>
              {item.author && (
                <p className="text-xs text-white/40 mt-0.5 truncate">{item.author}</p>
              )}
            </div>
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 text-white/20 hover:text-white/60 transition-colors mt-0.5"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          {/* Score bar */}
          <div className="flex items-center gap-2 mt-2">
            <div className="flex-1 h-1 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-violet-500/60"
                style={{ width: `${Math.min(item.composite_score, 100)}%` }}
              />
            </div>
            <span className="text-xs text-white/30 flex-shrink-0">
              {item.composite_score.toFixed(0)}
            </span>
          </div>

          {/* Feedback actions */}
          <div className="mt-3">
            <ResourceFeedbackActions
              resourceId={item.id}
              initialFeedback={item.user_feedback}
              onFeedbackChange={(fb) => setItem({ ...item, user_feedback: fb })}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function BookmarksPage() {
  const [resources, setResources] = useState<ResourceOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUserBookmarks()
      .then(setResources)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white">
      <div className="max-w-3xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-2xl bg-violet-500/20 flex items-center justify-center">
            <Bookmark className="w-5 h-5 text-violet-400 fill-violet-400/20" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Bookmarks</h1>
            <p className="text-sm text-white/40">Your saved learning resources</p>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-28 rounded-2xl bg-white/[0.03] border border-white/5 animate-pulse" />
            ))}
          </div>
        ) : resources.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Bookmark className="w-12 h-12 text-white/10 mb-4" />
            <h2 className="text-lg font-medium text-white/50 mb-2">No bookmarks yet</h2>
            <p className="text-sm text-white/30 max-w-sm">
              While browsing resources for a topic, click the Save button to bookmark them here.
            </p>
            <Link
              href="/explore"
              className="mt-6 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium transition-colors"
            >
              Browse Topics
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {resources.map((r) => (
              <ResourceCard key={r.id} resource={r} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
