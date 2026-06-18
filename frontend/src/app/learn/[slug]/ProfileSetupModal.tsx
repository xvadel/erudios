"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Sparkles, Brain, Award, Target } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProfileSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function ProfileSetupModal({ isOpen, onClose, onSaved }: ProfileSetupModalProps) {
  const { user, updateUserProfile } = useAuth();
  const [level, setLevel] = useState("beginner");
  const [learningStyle, setLearningStyle] = useState("practical");
  const [goal, setGoal] = useState("general");
  const [isSaving, setIsSaving] = useState(false);

  // Load user profile defaults on open
  useEffect(() => {
    if (user) {
      const timer = setTimeout(() => {
        setLevel(user.level || "beginner");
        setLearningStyle(user.learning_style || "practical");
        setGoal(user.goal || "general");
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [user, isOpen]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateUserProfile({
        level,
        learning_style: learningStyle,
        goal,
      });
      onSaved();
    } catch (error) {
      console.error("Failed to update profile", error);
    } finally {
      setIsSaving(false);
    }
  };

  const levels = [
    { id: "beginner", title: "Beginner", desc: "Start from scratch, focus on core concepts" },
    { id: "intermediate", title: "Intermediate", desc: "Build on existing basics with hands-on depth" },
    { id: "advanced", title: "Advanced", desc: "Dive deep into optimization, theory, and architecture" },
  ];

  const styles = [
    { id: "practical", title: "Practical", desc: "Run code & build projects" },
    { id: "research", title: "Research-driven", desc: "Read papers & analyze math" },
    { id: "interview", title: "Interview Prep", desc: "Solve challenges & patterns" },
    { id: "visual", title: "Visual-first", desc: "Diagrams & mental models" },
    { id: "project", title: "Project-based", desc: "Build end-to-end systems" },
  ];

  const goals = [
    { id: "general", title: "General", desc: "Broad exploration & curiosity" },
    { id: "job", title: "Job-ready", desc: "Skill up for professional roles" },
    { id: "startup", title: "Startup", desc: "Ship products & launch ideas" },
    { id: "academic", title: "Academic", desc: "Succeed in formal coursework" },
    { id: "research", title: "Researcher", desc: "Publish papers & contribute" },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-zinc-950/95 border border-zinc-800 text-white rounded-xl shadow-2xl backdrop-blur-md overflow-hidden max-h-[90vh] flex flex-col p-0">
        
        {/* Decorative Header Overlay */}
        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-violet-600 via-indigo-600 to-cyan-500" />
        
        <div className="p-6 md:p-8 flex-1 overflow-y-auto space-y-6">
          <DialogHeader className="text-left space-y-2">
            <DialogTitle className="text-2xl font-bold flex items-center gap-2 bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
              <Sparkles className="w-6 h-6 text-violet-400 animate-pulse" />
              Personalize Your Learning Journey
            </DialogTitle>
            <DialogDescription className="text-zinc-400 text-sm">
              We customize the curriculum topics, explanations, code blocks, and quizzes based on your profile.
            </DialogDescription>
          </DialogHeader>

          {/* Level Selection */}
          <div className="space-y-3">
            <label className="text-sm font-semibold flex items-center gap-2 text-zinc-300">
              <Award className="w-4 h-4 text-violet-400" />
              What is your current level?
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {levels.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setLevel(item.id)}
                  type="button"
                  className={cn(
                    "flex flex-col text-left p-3.5 rounded-lg border text-sm transition-all duration-200 cursor-pointer",
                    level === item.id
                      ? "bg-violet-600/10 border-violet-500 shadow-[0_0_12px_rgba(124,58,237,0.15)] text-white"
                      : "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700 text-zinc-300 hover:text-white"
                  )}
                >
                  <span className="font-semibold text-zinc-100">{item.title}</span>
                  <span className="text-xs text-zinc-400 mt-1">{item.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Learning Style Selection */}
          <div className="space-y-3">
            <label className="text-sm font-semibold flex items-center gap-2 text-zinc-300">
              <Brain className="w-4 h-4 text-indigo-400" />
              Preferred Learning Style?
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              {styles.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setLearningStyle(item.id)}
                  type="button"
                  className={cn(
                    "flex flex-col text-left p-3 rounded-lg border text-xs transition-all duration-200 cursor-pointer",
                    learningStyle === item.id
                      ? "bg-indigo-600/10 border-indigo-500 shadow-[0_0_12px_rgba(99,102,241,0.15)] text-white"
                      : "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700 text-zinc-350 hover:text-white"
                  )}
                >
                  <span className="font-semibold text-zinc-100">{item.title}</span>
                  <span className="text-[11px] text-zinc-400 mt-0.5">{item.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Goals Selection */}
          <div className="space-y-3">
            <label className="text-sm font-semibold flex items-center gap-2 text-zinc-300">
              <Target className="w-4 h-4 text-cyan-400" />
              What is your primary goal?
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              {goals.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setGoal(item.id)}
                  type="button"
                  className={cn(
                    "flex flex-col text-left p-3 rounded-lg border text-xs transition-all duration-200 cursor-pointer",
                    goal === item.id
                      ? "bg-cyan-600/10 border-cyan-500 shadow-[0_0_12px_rgba(6,182,212,0.15)] text-white"
                      : "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700 text-zinc-350 hover:text-white"
                  )}
                >
                  <span className="font-semibold text-zinc-100">{item.title}</span>
                  <span className="text-[11px] text-zinc-400 mt-0.5">{item.desc}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter className="bg-zinc-900/40 border-t border-zinc-800 p-4 md:p-6 flex flex-row items-center justify-between gap-3 shrink-0">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={isSaving}
            className="text-zinc-400 hover:text-white hover:bg-zinc-800 border-0"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving}
            className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold shadow-lg hover:shadow-violet-900/30 transition-all px-6"
          >
            {isSaving ? "Saving..." : "Start Learning"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
