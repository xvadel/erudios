"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getTopic,
  getTopicChildren,
  getPrerequisites,
  getWhatsNext,
  getResources,
  triggerDiscovery,
  type Topic,
  type Dependency,
  type WhatsNextResponse,
  type Resource,
} from "@/lib/api";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ChevronRight,
  Clock,
  ExternalLink,
  GitBranch,
  Lock,
  RefreshCw,
  Sparkles,
  Star,
  Unlock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function TopicDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();

  const [topic, setTopic] = useState<Topic | null>(null);
  const [children, setChildren] = useState<Topic[]>([]);
  const [prerequisites, setPrerequisites] = useState<Dependency[]>([]);
  const [whatsNext, setWhatsNext] = useState<WhatsNextResponse | null>(null);
  const [resources, setResources] = useState<Resource[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "resources" | "path">("overview");

  useEffect(() => {
    if (!slug) return;
    setLoading(true);

    Promise.all([
      getTopic(slug),
      getTopicChildren(slug),
      getPrerequisites(slug),
      getWhatsNext(slug),
      getResources(slug),
    ])
      .then(([t, ch, prereqs, next, res]) => {
        setTopic(t);
        setChildren(ch);
        setPrerequisites(prereqs);
        setWhatsNext(next);
        setResources(res);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [slug]);

  const handleDiscover = async () => {
    if (!slug) return;
    setDiscovering(true);
    try {
      await triggerDiscovery(slug);
      // Poll for resources after a delay
      setTimeout(async () => {
        const res = await getResources(slug);
        setResources(res);
        setDiscovering(false);
      }, 5000);
    } catch {
      setDiscovering(false);
    }
  };

  if (loading) return <TopicDetailSkeleton />;
  if (!topic) return <div className="pt-28 text-center text-muted-foreground">Topic not found.</div>;

  return (
    <div className="max-w-6xl mx-auto px-4 pt-24 pb-20">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8">
        <Link href="/explore" className="hover:text-foreground transition-colors flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" />
          Explore
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="text-foreground">{topic.name}</span>
      </div>

      {/* Hero */}
      <div className="mb-10">
        <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2">
              {topic.name}
            </h1>
            {topic.description && (
              <p className="text-muted-foreground max-w-2xl leading-relaxed">{topic.description}</p>
            )}
          </div>
          <div className="flex flex-wrap gap-2 shrink-0">
            <span className={cn(
              "text-sm px-3 py-1 rounded-full font-medium",
              topic.difficulty === "beginner" && "badge-beginner",
              topic.difficulty === "intermediate" && "badge-intermediate",
              topic.difficulty === "advanced" && "badge-advanced",
            )}>
              {topic.difficulty}
            </span>
            <span className="flex items-center gap-1.5 text-sm px-3 py-1 rounded-full bg-white/5 border border-white/10 text-muted-foreground">
              <Clock className="w-3.5 h-3.5" />
              {topic.estimated_hours}h estimated
            </span>
          </div>
        </div>

        {/* CTA */}
        <div className="flex flex-wrap gap-3">
          <Button
            className="bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white shadow-lg shadow-indigo-500/25"
            onClick={() => router.push(`/learn/${slug}`)}
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Build My Curriculum
          </Button>
          <Button
            variant="outline"
            className="border-white/15 hover:border-white/25 bg-white/5"
            onClick={handleDiscover}
            disabled={discovering}
          >
            <RefreshCw className={cn("w-4 h-4 mr-2", discovering && "animate-spin")} />
            {discovering ? "Discovering…" : "Discover Resources"}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-8 bg-white/5 rounded-xl p-1 w-fit">
        {(["overview", "resources", "path"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2 text-sm rounded-lg font-medium transition-all duration-200",
              activeTab === tab
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/25"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Prerequisites */}
          <div className="lg:col-span-1 space-y-6">
            <PrerequisitesCard prerequisites={prerequisites} />
            <WhatsNextCard whatsNext={whatsNext} />
          </div>

          {/* Sub-topics */}
          <div className="lg:col-span-2">
            {children.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-indigo-400" />
                  Sub-topics
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {children.map((child) => (
                    <Link
                      key={child.id}
                      href={`/explore/${child.slug}`}
                      className="glass-hover rounded-xl p-4 group"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <span className="font-medium text-sm">{child.name}</span>
                        <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 group-hover:translate-x-0.5 transition-transform" />
                      </div>
                      {child.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2">{child.description}</p>
                      )}
                      <div className="flex items-center gap-2 mt-3">
                        <span className={cn(
                          "text-xs px-2 py-0.5 rounded-full",
                          child.difficulty === "beginner" && "badge-beginner",
                          child.difficulty === "intermediate" && "badge-intermediate",
                          child.difficulty === "advanced" && "badge-advanced",
                        )}>
                          {child.difficulty}
                        </span>
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="w-3 h-3" />{child.estimated_hours}h
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "resources" && (
        <ResourcesTab resources={resources} onDiscover={handleDiscover} discovering={discovering} />
      )}

      {activeTab === "path" && (
        <LearningPathTab topicSlug={slug} />
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function PrerequisitesCard({ prerequisites }: { prerequisites: Dependency[] }) {
  if (prerequisites.length === 0) return null;
  return (
    <div className="glass rounded-xl p-5">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
        <Lock className="w-3.5 h-3.5" />
        Prerequisites
      </h3>
      <div className="space-y-3">
        {prerequisites.map(({ topic, reason }) => (
          <div key={topic.id}>
            <Link
              href={`/explore/${topic.slug}`}
              className="flex items-center justify-between text-sm font-medium hover:text-indigo-400 transition-colors"
            >
              {topic.name}
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
            </Link>
            {reason && (
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{reason}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function WhatsNextCard({ whatsNext }: { whatsNext: WhatsNextResponse | null }) {
  if (!whatsNext?.next_steps.length) return null;
  return (
    <div className="glass rounded-xl p-5 border border-emerald-500/15">
      <h3 className="text-sm font-semibold text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-2">
        <Unlock className="w-3.5 h-3.5" />
        What to Learn Next
      </h3>
      <div className="space-y-3">
        {whatsNext.next_steps.slice(0, 3).map(({ topic, reason }) => (
          <div key={topic.id}>
            <Link
              href={`/explore/${topic.slug}`}
              className="flex items-center justify-between text-sm font-medium hover:text-emerald-400 transition-colors"
            >
              {topic.name}
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
            </Link>
            {reason && (
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{reason}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

const SOURCE_LABELS: Record<string, string> = {
  paper: "Paper",
  github: "GitHub",
  blog: "Blog",
  course: "Course",
  video: "Video",
  documentation: "Docs",
  book: "Book",
};

function ResourcesTab({
  resources,
  onDiscover,
  discovering,
}: {
  resources: Resource[];
  onDiscover: () => void;
  discovering: boolean;
}) {
  if (resources.length === 0) {
    return (
      <div className="text-center py-16 space-y-4">
        <BookOpen className="w-10 h-10 text-muted-foreground mx-auto" />
        <p className="text-muted-foreground">No resources discovered yet.</p>
        <Button
          variant="outline"
          onClick={onDiscover}
          disabled={discovering}
          className="border-white/15"
        >
          <RefreshCw className={cn("w-4 h-4 mr-2", discovering && "animate-spin")} />
          Discover Resources
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {resources.map((r) => (
        <a
          key={r.id}
          href={r.url}
          target="_blank"
          rel="noopener noreferrer"
          className="glass-hover rounded-xl p-4 flex items-start justify-between gap-4 group"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={cn(
                "text-xs px-2 py-0.5 rounded-full font-medium shrink-0",
                `badge-${r.source_type}`
              )}>
                {SOURCE_LABELS[r.source_type] || r.source_type}
              </span>
              {r.author && (
                <span className="text-xs text-muted-foreground truncate">{r.author}</span>
              )}
            </div>
            <p className="text-sm font-medium text-foreground group-hover:text-indigo-300 transition-colors line-clamp-1">
              {r.title}
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <div className="flex items-center gap-1">
              <Star className="w-3 h-3 text-amber-400" />
              <span className="text-xs text-muted-foreground">{Math.round(r.composite_score)}</span>
            </div>
            <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
          </div>
        </a>
      ))}
    </div>
  );
}

function LearningPathTab({ topicSlug }: { topicSlug: string }) {
  const [path, setPath] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    import("@/lib/api").then(({ getLearningPath }) =>
      getLearningPath(topicSlug)
        .then(setPath)
        .finally(() => setLoading(false))
    );
  }, [topicSlug]);

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="shimmer h-14 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-muted-foreground mb-6">
        Topologically sorted learning order based on prerequisites — start from the top.
      </p>
      {path.map((t, i) => (
        <Link
          key={t.id}
          href={`/explore/${t.slug}`}
          className="flex items-center gap-4 glass-hover rounded-xl px-5 py-3.5 group animate-fade-in-up"
          style={{ animationDelay: `${i * 0.04}s`, opacity: 0 }}
        >
          <span className="text-xs font-mono text-muted-foreground w-6 shrink-0">
            {String(i + 1).padStart(2, "0")}
          </span>
          <div className="flex-1">
            <span className="text-sm font-medium group-hover:text-indigo-300 transition-colors">
              {t.name}
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className={cn(
              "text-xs px-2 py-0.5 rounded-full",
              t.difficulty === "beginner" && "badge-beginner",
              t.difficulty === "intermediate" && "badge-intermediate",
              t.difficulty === "advanced" && "badge-advanced",
            )}>
              {t.difficulty}
            </span>
            <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
          </div>
        </Link>
      ))}
    </div>
  );
}

function TopicDetailSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-4 pt-24 pb-20 space-y-8">
      <div className="shimmer h-4 w-32 rounded" />
      <div className="space-y-3">
        <div className="shimmer h-10 w-64 rounded" />
        <div className="shimmer h-4 w-full max-w-xl rounded" />
        <div className="shimmer h-4 w-80 rounded" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-3">
          <div className="shimmer h-40 rounded-xl" />
          <div className="shimmer h-32 rounded-xl" />
        </div>
        <div className="lg:col-span-2 grid grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="shimmer h-24 rounded-xl" />
          ))}
        </div>
      </div>
    </div>
  );
}
