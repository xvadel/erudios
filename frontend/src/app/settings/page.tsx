"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  BookOpen,
  Brain,
  ChevronRight,
  Eye,
  GraduationCap,
  KeyRound,
  LogOut,
  Save,
  ShieldCheck,
  Target,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

// ── Constants ──────────────────────────────────────────────────────────────────

const LEVELS = [
  {
    id: "beginner",
    label: "Beginner",
    desc: "New to AI/ML concepts",
    color: "border-emerald-500/30 hover:border-emerald-500/60",
    active: "border-emerald-500 bg-emerald-500/10 text-emerald-400",
  },
  {
    id: "intermediate",
    label: "Intermediate",
    desc: "Familiar with basics",
    color: "border-amber-500/30 hover:border-amber-500/60",
    active: "border-amber-500 bg-amber-500/10 text-amber-400",
  },
  {
    id: "advanced",
    label: "Advanced",
    desc: "Deep technical background",
    color: "border-rose-500/30 hover:border-rose-500/60",
    active: "border-rose-500 bg-rose-500/10 text-rose-400",
  },
];

const STYLES = [
  { id: "practical", label: "Hands-on", desc: "Code, exercises, projects", icon: "🛠️" },
  { id: "visual", label: "Visual", desc: "Diagrams, analogies, models", icon: "🎨" },
  { id: "research", label: "Research", desc: "Papers, theory, depth", icon: "📚" },
  { id: "interview", label: "Interview Prep", desc: "Q&A, coding challenges", icon: "🎯" },
  { id: "project", label: "Project-based", desc: "Real-world applications", icon: "🚀" },
];

const GOALS = [
  { id: "general", label: "General Learning", icon: BookOpen },
  { id: "job", label: "Get a Job", icon: Target },
  { id: "research", label: "Research", icon: Brain },
  { id: "startup", label: "Build a Startup", icon: GraduationCap },
  { id: "academic", label: "Academic Study", icon: ShieldCheck },
];

// ── Page ───────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const { user, updateUserProfile, logout } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const [level, setLevel] = useState(user?.level ?? "beginner");
  const [learningStyle, setLearningStyle] = useState(user?.learning_style ?? "practical");
  const [goal, setGoal] = useState(user?.goal ?? "general");
  const [name, setName] = useState(user?.name ?? "");
  const [saving, setSaving] = useState(false);

  if (!user) {
    router.push("/auth/login");
    return null;
  }

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateUserProfile({ level, learning_style: learningStyle, goal, name: name.trim() || undefined });
      toast({ title: "Profile saved", description: "Your learning preferences have been updated." });
    } catch {
      toast({ title: "Failed to save profile", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  return (
    <div className="max-w-2xl mx-auto px-4 pt-24 pb-20 space-y-10">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight mb-1">Settings</h1>
        <p className="text-muted-foreground">Personalize your learning experience</p>
      </div>

      {/* Account info */}
      <Section title="Account" icon={User}>
        <div className="flex items-center gap-4 p-4 glass rounded-xl">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center text-white text-lg font-bold">
            {(user.name || user.username)[0].toUpperCase()}
          </div>
          <div>
            <p className="font-semibold">{user.name || user.username}</p>
            <p className="text-sm text-muted-foreground">@{user.username}</p>
          </div>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="display-name" className="text-sm font-medium text-muted-foreground">
            Display Name
          </label>
          <input
            id="display-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={user.username}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-indigo-500/50 transition-colors"
          />
        </div>
      </Section>

      {/* Knowledge level */}
      <Section title="Knowledge Level" icon={GraduationCap}>
        <div className="grid grid-cols-3 gap-3">
          {LEVELS.map((l) => (
            <button
              key={l.id}
              id={`level-${l.id}`}
              onClick={() => setLevel(l.id)}
              className={cn(
                "p-4 rounded-xl border text-left transition-all",
                level === l.id ? l.active : "border-white/10 hover:border-white/20 text-muted-foreground"
              )}
            >
              <p className="font-semibold text-sm">{l.label}</p>
              <p className="text-xs mt-0.5 opacity-75">{l.desc}</p>
            </button>
          ))}
        </div>
      </Section>

      {/* Learning style */}
      <Section title="Learning Style" icon={Brain}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {STYLES.map((s) => (
            <button
              key={s.id}
              id={`style-${s.id}`}
              onClick={() => setLearningStyle(s.id)}
              className={cn(
                "flex items-start gap-3 p-3.5 rounded-xl border text-left transition-all",
                learningStyle === s.id
                  ? "border-indigo-500 bg-indigo-500/10"
                  : "border-white/10 hover:border-white/20"
              )}
            >
              <span className="text-xl">{s.icon}</span>
              <div>
                <p className={cn("font-semibold text-sm", learningStyle === s.id ? "text-indigo-300" : "")}>
                  {s.label}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">{s.desc}</p>
              </div>
              {learningStyle === s.id && (
                <div className="ml-auto shrink-0 w-2 h-2 rounded-full bg-indigo-500 mt-1" />
              )}
            </button>
          ))}
        </div>
      </Section>

      {/* Learning goal */}
      <Section title="Learning Goal" icon={Target}>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          {GOALS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`goal-${id}`}
              onClick={() => setGoal(id)}
              className={cn(
                "flex items-center gap-2.5 p-3 rounded-xl border text-sm transition-all",
                goal === id
                  ? "border-violet-500 bg-violet-500/10 text-violet-300"
                  : "border-white/10 hover:border-white/20 text-muted-foreground"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="font-medium">{label}</span>
            </button>
          ))}
        </div>
      </Section>

      {/* Save */}
      <Button
        id="settings-save-btn"
        onClick={handleSave}
        disabled={saving}
        className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-500/20 h-11"
      >
        {saving ? (
          <>Saving…</>
        ) : (
          <>
            <Save className="w-4 h-4 mr-2" />
            Save Preferences
          </>
        )}
      </Button>

      {/* Danger zone */}
      <div className="border border-rose-500/20 rounded-2xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-rose-400 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4" />
          Account Actions
        </h3>
        <button
          id="settings-logout-btn"
          onClick={handleLogout}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-rose-400 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out of Erudios
        </button>
      </div>
    </div>
  );
}

// ── Section wrapper ────────────────────────────────────────────────────────────

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-muted-foreground uppercase tracking-wider">
        <Icon className="w-4 h-4" />
        {title}
      </h2>
      <div className="space-y-3">{children}</div>
    </div>
  );
}
