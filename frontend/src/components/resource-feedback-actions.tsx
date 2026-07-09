"use client";

import { useState } from "react";
import { submitResourceFeedback, type ResourceFeedback } from "@/lib/api";
import { Bookmark, ThumbsUp, ThumbsDown, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

interface ResourceFeedbackActionsProps {
  resourceId: string;
  initialFeedback: ResourceFeedback | null;
  onFeedbackChange?: (feedback: ResourceFeedback) => void;
}

export function ResourceFeedbackActions({
  resourceId,
  initialFeedback,
  onFeedbackChange,
}: ResourceFeedbackActionsProps) {
  const { toast } = useToast();
  const [feedback, setFeedback] = useState<ResourceFeedback | null>(initialFeedback);
  const [loading, setLoading] = useState<string | null>(null);

  async function update(data: Parameters<typeof submitResourceFeedback>[1]) {
    const key = Object.keys(data)[0];
    setLoading(key);
    try {
      const updated = await submitResourceFeedback(resourceId, data);
      setFeedback(updated);
      onFeedbackChange?.(updated);
    } catch {
      toast({ title: "Failed to save", variant: "destructive" });
    } finally {
      setLoading(null);
    }
  }

  const isBookmarked = feedback?.bookmarked ?? false;
  const isCompleted = feedback?.completed ?? false;
  const currentRating = feedback?.rating ?? 0;

  return (
    <div className="flex items-center gap-1.5">
      {/* Bookmark */}
      <button
        onClick={() => update({ bookmarked: !isBookmarked })}
        disabled={loading === "bookmarked"}
        aria-label={isBookmarked ? "Remove bookmark" : "Bookmark resource"}
        className={cn(
          "flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all",
          isBookmarked
            ? "bg-violet-500/20 text-violet-400 border border-violet-500/30 hover:bg-violet-500/30"
            : "bg-white/5 text-white/40 border border-white/10 hover:bg-white/10 hover:text-white/70"
        )}
      >
        <Bookmark className={cn("w-3.5 h-3.5", isBookmarked && "fill-current")} />
        {isBookmarked ? "Saved" : "Save"}
      </button>

      {/* Thumbs Up */}
      <button
        onClick={() => update({ rating: currentRating === 1 ? 0 : 1 })}
        disabled={loading === "rating"}
        aria-label="Rate helpful"
        className={cn(
          "flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all",
          currentRating === 1
            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30"
            : "bg-white/5 text-white/40 border border-white/10 hover:bg-white/10 hover:text-white/70"
        )}
      >
        <ThumbsUp className="w-3.5 h-3.5" />
      </button>

      {/* Thumbs Down */}
      <button
        onClick={() => update({ rating: currentRating === -1 ? 0 : -1 })}
        disabled={loading === "rating"}
        aria-label="Rate not helpful"
        className={cn(
          "flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all",
          currentRating === -1
            ? "bg-rose-500/20 text-rose-400 border border-rose-500/30 hover:bg-rose-500/30"
            : "bg-white/5 text-white/40 border border-white/10 hover:bg-white/10 hover:text-white/70"
        )}
      >
        <ThumbsDown className="w-3.5 h-3.5" />
      </button>

      {/* Mark Complete */}
      <button
        onClick={() => update({ completed: !isCompleted })}
        disabled={loading === "completed"}
        aria-label={isCompleted ? "Mark incomplete" : "Mark completed"}
        className={cn(
          "flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all",
          isCompleted
            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30"
            : "bg-white/5 text-white/40 border border-white/10 hover:bg-white/10 hover:text-white/70"
        )}
      >
        <CheckCircle2 className={cn("w-3.5 h-3.5", isCompleted && "fill-current/20")} />
        {isCompleted ? "Done" : "Mark Done"}
      </button>
    </div>
  );
}
