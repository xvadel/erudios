"use client";

import { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  createCurriculum,
  getCurriculumProgress,
  type Curriculum,
  type CurriculumProgress,
} from "@/lib/api";
import { ProfileSetupModal } from "./ProfileSetupModal";
import { ModuleContent } from "./ModuleContent";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { Button, buttonVariants } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Brain,
  ChevronLeft,
  Settings,
  Compass,
  ArrowRight,
  Sparkles,
  Trophy,
  Clock,
  Gauge,
  GraduationCap,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PageProps {
  params: Promise<{ slug: string }>;
}

const GEN_STEPS = [
  "Analyzing syllabus topics and dependencies...",
  "Synthesizing prerequisite paths...",
  "Structuring module descriptions & study weights...",
  "Generating quiz datasets and overlay parameters...",
  "Personalizing learning style views...",
];

export default function LearnPage({ params }: PageProps) {
  const { slug } = use(params);
  const { user, loading: authLoading, hasCustomProfile } = useAuth();

  // Curriculum states
  const [curriculum, setCurriculum] = useState<Curriculum | null>(null);
  const [progress, setProgress] = useState<CurriculumProgress | null>(null);
  const [loadingCurriculum, setLoadingCurriculum] = useState(false);
  const [activeModuleId, setActiveModuleId] = useState<string | null>(null);

  // Onboarding Modal state
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  // Generation steps animation
  const [genStep, setGenStep] = useState(0);

  // Increment loading steps while generating
  useEffect(() => {
    if (!loadingCurriculum) return;
    const interval = setInterval(() => {
      setGenStep((prev) => (prev < GEN_STEPS.length - 1 ? prev + 1 : prev));
    }, 1200);
    return () => clearInterval(interval);
  }, [loadingCurriculum]);

  // Main loader function
  const loadCurriculum = useCallback(async () => {
    setLoadingCurriculum(true);
    try {
      const curr = await createCurriculum(slug);
      setCurriculum(curr);
      if (curr.modules.length > 0) {
        setActiveModuleId(curr.modules[0].id);
      }

      // Fetch progress
      const prog = await getCurriculumProgress(curr.id);
      setProgress(prog);
    } catch (err) {
      console.error("Failed to build curriculum", err);
    } finally {
      setLoadingCurriculum(false);
    }
  }, [slug]);

  // Check onboarding condition on user load
  useEffect(() => {
    if (authLoading) return;
    if (!user) return; // Wait until they auth or prompt them to auth

    // If they haven't customized their profile, open the modal asynchronously
    if (!hasCustomProfile) {
      const timer = setTimeout(() => {
        setIsProfileModalOpen(true);
      }, 0);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        loadCurriculum();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [user, authLoading, hasCustomProfile, loadCurriculum]);

  // Load progress details
  const refreshProgress = useCallback(async () => {
    if (!curriculum) return;
    try {
      const prog = await getCurriculumProgress(curriculum.id);
      setProgress(prog);
    } catch (err) {
      console.error("Failed to refresh progress", err);
    }
  }, [curriculum]);


  // Helper mapping
  const styleDisplayNames: Record<string, string> = {
    practical: "Hands-on Practical",
    research: "Research-driven Theory",
    interview: "Interview & Coding",
    visual: "Visual Models",
    project: "Project Builder",
  };

  const goalDisplayNames: Record<string, string> = {
    general: "General Exploration",
    job: "Career Upgrade",
    startup: "AI Startup",
    academic: "Academic Study",
    research: "Academic Research",
  };

  // Auth Guard: Loading User
  if (authLoading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex flex-col justify-center items-center gap-4">
        <div className="w-8 h-8 rounded-full border-4 border-violet-600/30 border-t-violet-500 animate-spin" />
        <p className="text-zinc-500 text-sm">Authenticating...</p>
      </div>
    );
  }

  // Auth Guard: Unauthenticated Guest
  if (!user) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(124,58,237,0.06),rgba(255,255,255,0))]" />
        
        <Card className="max-w-md w-full bg-zinc-900/40 border-zinc-850 backdrop-blur-md text-center p-6 md:p-8 space-y-6 relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-violet-600 to-indigo-600" />
          
          <div className="w-16 h-16 bg-violet-600/10 border border-violet-500/25 rounded-2xl flex items-center justify-center mx-auto text-violet-400 shadow-[0_0_15px_rgba(124,58,237,0.1)]">
            <Brain className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold tracking-tight text-white">Unlock Your Curriculum</h2>
            <p className="text-zinc-400 text-sm leading-relaxed">
              Generate personalized syllabus tracks, customize content for your learning style, take section quizzes, and track your accomplishments.
            </p>
          </div>

          <div className="flex flex-col gap-2.5 pt-2">
            <Link
              href={`/auth/login?redirect=/learn/${slug}`}
              className={cn(
                buttonVariants({ variant: "default" }),
                "bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold shadow-lg hover:shadow-violet-900/20 cursor-pointer w-full text-center"
              )}
            >
              Sign In or Sign Up
              <ArrowRight className="w-4 h-4 ml-1.5" />
            </Link>
            <Link
              href="/explore"
              className={cn(
                buttonVariants({ variant: "outline" }),
                "border-zinc-800 bg-zinc-900/40 hover:bg-zinc-850 text-zinc-350 hover:text-white cursor-pointer w-full text-center"
              )}
            >
              <Compass className="w-4 h-4 mr-1.5" />
              Browse Topics
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  // Generation state
  if (loadingCurriculum) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(124,58,237,0.08),rgba(255,255,255,0))]" />
        
        <div className="max-w-md w-full text-center space-y-6">
          <div className="relative w-20 h-20 mx-auto">
            {/* Spinning gradient ring */}
            <div className="absolute inset-0 rounded-full border-4 border-zinc-900" />
            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-violet-500 border-r-indigo-500 animate-spin" />
            <div className="absolute inset-2 bg-zinc-950 rounded-full flex items-center justify-center border border-zinc-850">
              <Sparkles className="w-6 h-6 text-violet-400 animate-pulse" />
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-xl font-bold bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
              Synthesizing Your Curriculum
            </h3>
            <p className="text-zinc-400 text-sm h-6 transition-all duration-300">
              {GEN_STEPS[genStep]}
            </p>
          </div>

          {/* Progress simulation */}
          <div className="w-full bg-zinc-900 border border-zinc-850 rounded-full h-2 overflow-hidden max-w-xs mx-auto">
            <div
              className="bg-gradient-to-r from-violet-600 to-indigo-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${((genStep + 1) / GEN_STEPS.length) * 100}%` }}
            />
          </div>
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold block">
            Usually takes 3 to 8 seconds
          </span>
        </div>
      </div>
    );
  }

  const activeModule = curriculum?.modules.find((m) => m.id === activeModuleId);
  const activeModuleProgress = progress?.progress.find((p) => p.module_id === activeModuleId);

  return (
    <div className="min-h-screen bg-zinc-950 text-white relative">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(124,58,237,0.04),rgba(255,255,255,0))]" />
      
      <div className="max-w-[1400px] mx-auto px-4 py-6 md:py-8 space-y-6 relative z-10">
        {/* Back Link */}
        <div className="flex justify-between items-center">
          <Link
            href={`/explore/${slug}`}
            className="flex items-center text-xs md:text-sm text-zinc-400 hover:text-white font-medium group transition-colors"
          >
            <ChevronLeft className="w-4 h-4 mr-1 group-hover:-translate-x-0.5 transition-transform" />
            Back to Explore
          </Link>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsProfileModalOpen(true)}
            className="text-xs text-zinc-400 hover:text-white hover:bg-zinc-900 border border-zinc-900 gap-1.5 cursor-pointer"
          >
            <Settings className="w-3.5 h-3.5" />
            Adjust Path Settings
          </Button>
        </div>

        {/* Curriculum Header Card */}
        {curriculum && (
          <div className="p-6 rounded-2xl bg-zinc-900/30 border border-zinc-850 backdrop-blur-md flex flex-col md:flex-row gap-6 justify-between items-start md:items-center">
            <div className="space-y-3 flex-1">
              <div>
                <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
                  <GraduationCap className="w-7 h-7 text-indigo-400 shrink-0" />
                  {curriculum.topic_name} Learning Curriculum
                </h1>
                <p className="text-xs md:text-sm text-zinc-400 mt-1">
                  Tailored learning path specifically constructed for your academic preferences.
                </p>
              </div>

              {/* Profile Config Badges */}
              <div className="flex flex-wrap gap-2">
                <Badge className="bg-violet-950/40 text-violet-400 border border-violet-900/60 capitalize flex items-center gap-1 font-semibold text-xs">
                  <Gauge className="w-3.5 h-3.5" />
                  {curriculum.level} Level
                </Badge>
                <Badge className="bg-indigo-950/40 text-indigo-400 border border-indigo-900/60 flex items-center gap-1 font-semibold text-xs">
                  <Brain className="w-3.5 h-3.5" />
                  {styleDisplayNames[curriculum.learning_style] || curriculum.learning_style}
                </Badge>
                <Badge className="bg-cyan-950/40 text-cyan-400 border border-cyan-900/60 flex items-center gap-1 font-semibold text-xs">
                  <Clock className="w-3.5 h-3.5" />
                  {goalDisplayNames[curriculum.goal] || curriculum.goal}
                </Badge>
              </div>
            </div>

            {/* Curriculum Progress Display */}
            {progress && (
              <div className="w-full md:w-64 space-y-2 p-4 rounded-xl border border-zinc-850 bg-zinc-950/40 shrink-0">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-zinc-400 font-medium flex items-center gap-1">
                    <Trophy className="w-3.5 h-3.5 text-amber-400" /> Syllabus Progress
                  </span>
                  <span className="font-bold text-white">{progress.completion_pct}%</span>
                </div>
                <Progress value={progress.completion_pct} className="h-2 bg-zinc-900" />
                <div className="text-[10px] text-zinc-500 text-right">
                  {progress.completed_modules} of {progress.total_modules} modules completed
                </div>
              </div>
            )}
          </div>
        )}

        {/* Core Layout Grid */}
        {curriculum && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* Sidebar Module List */}
            <div className="lg:col-span-4 space-y-3">
              <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-wider px-1">
                Learning Modules
              </h2>
              <div className="space-y-2 max-h-[75vh] overflow-y-auto pr-1">
                {curriculum.modules.map((mod, index) => {
                  const isActive = mod.id === activeModuleId;
                  const modProgress = progress?.progress.find((p) => p.module_id === mod.id);
                  const isModCompleted = modProgress ? modProgress.mastery_score >= 80 : false;

                  return (
                    <button
                      key={mod.id}
                      onClick={() => setActiveModuleId(mod.id)}
                      className={cn(
                        "w-full text-left p-4 rounded-xl border transition-all duration-200 cursor-pointer flex gap-3.5 relative overflow-hidden group",
                        isActive
                          ? "bg-violet-950/15 border-violet-500 shadow-[0_4px_20px_rgba(124,58,237,0.06)]"
                          : "bg-zinc-900/30 border-zinc-850 hover:border-zinc-800 hover:bg-zinc-900/50"
                      )}
                    >
                      {/* Active Indicator bar */}
                      {isActive && (
                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-violet-500" />
                      )}

                      {/* Number bubble */}
                      <span
                        className={cn(
                          "w-6 h-6 rounded-full border text-xs font-bold flex items-center justify-center shrink-0 mt-0.5",
                          isActive
                            ? "bg-violet-500 text-white border-violet-400"
                            : isModCompleted
                            ? "bg-green-950/40 text-green-400 border-green-900"
                            : "bg-zinc-950/60 border-zinc-800 text-zinc-400"
                        )}
                      >
                        {index + 1}
                      </span>

                      <div className="flex-1 space-y-1">
                        <div className="flex justify-between items-start gap-2">
                          <span
                            className={cn(
                              "font-semibold text-sm leading-tight transition-colors",
                              isActive
                                ? "text-white"
                                : isModCompleted
                                ? "text-zinc-300 group-hover:text-white"
                                : "text-zinc-400 group-hover:text-zinc-200"
                            )}
                          >
                            {mod.title}
                          </span>
                          {isModCompleted && (
                            <Badge className="bg-green-500/10 border-green-500/20 text-green-400 text-[10px] shrink-0 font-semibold px-1.5 py-0.5">
                              Done
                            </Badge>
                          )}
                        </div>

                        {/* Estimated time & difficulty */}
                        <div className="flex items-center gap-3 text-xs text-zinc-500 mt-1">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {mod.estimated_hours} hrs
                          </span>
                          <span className="capitalize">{mod.difficulty}</span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Main Content Pane */}
            <div className="lg:col-span-8">
              {activeModule && (
                <div className="p-6 md:p-8 rounded-2xl bg-zinc-900/30 border border-zinc-850 backdrop-blur-md space-y-6">
                  {/* Active Module Header */}
                  <div className="border-b border-zinc-850 pb-5 space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge className="bg-indigo-950/50 text-indigo-400 border border-indigo-900/60 text-[10px] font-semibold px-2 py-0.5">
                        Module {curriculum.modules.findIndex((m) => m.id === activeModuleId) + 1}
                      </Badge>
                      {activeModule.why_next && (
                        <span className="text-xs text-violet-400 font-semibold flex items-center gap-1">
                          <Sparkles className="w-3.5 h-3.5" />
                          {activeModule.why_next}
                        </span>
                      )}
                    </div>
                    <h2 className="text-xl md:text-2xl font-extrabold text-white">
                      {activeModule.title}
                    </h2>
                    <p className="text-zinc-400 text-sm leading-relaxed">
                      {activeModule.description}
                    </p>
                  </div>

                  {/* Module Content and Quiz components */}
                  <ModuleContent
                    moduleId={activeModule.id}
                    topicSlug={activeModule.topic_slug}
                    onProgressUpdate={refreshProgress}
                    isCompleted={activeModuleProgress ? activeModuleProgress.mastery_score >= 80 : false}
                    masteryScore={activeModuleProgress?.mastery_score || 0}
                    userStyle={curriculum.learning_style}
                  />
                </div>
              )}
            </div>

          </div>
        )}
      </div>

      {/* AI Tutor floating chat panel — only when curriculum is loaded */}
      {curriculum && (
        <ChatPanel
          topicSlug={activeModule?.topic_slug ?? slug}
          topicName={activeModule?.topic_name ?? curriculum.topic_name}
        />
      )}

      {/* Settings / Onboarding modal */}
      <ProfileSetupModal
        isOpen={isProfileModalOpen}
        onClose={() => {
          setIsProfileModalOpen(false);
          if (!curriculum && !loadingCurriculum) {
            loadCurriculum();
          }
        }}
        onSaved={() => {
          setIsProfileModalOpen(false);
          loadCurriculum();
        }}
      />
    </div>
  );
}
