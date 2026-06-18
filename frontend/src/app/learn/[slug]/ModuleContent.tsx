"use client";

import { useState, useEffect } from "react";
import {
  getArtifactShell,
  getSectionContent,
  getSectionQuiz,
  completeModule,
  submitQuizResult,
  type ArtifactShell,
  type SectionContent,
  type QuizData,
} from "@/lib/api";
import { MarkdownRenderer } from "@/components/ui/markdown-renderer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  BookOpen,
  Award,
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  ChevronRight,
  ArrowRight,
  RefreshCw,
  Sparkles,
  BookmarkCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ModuleContentProps {
  moduleId: string;
  topicSlug: string;
  onProgressUpdate: () => void;
  isCompleted: boolean;
  masteryScore: number;
  userStyle?: string;
}

export function ModuleContent({
  moduleId,
  topicSlug,
  onProgressUpdate,
  isCompleted,
  masteryScore,
  userStyle,
}: ModuleContentProps) {
  const [shell, setShell] = useState<ArtifactShell | null>(null);
  const [loadingShell, setLoadingShell] = useState(true);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [sectionContent, setSectionContent] = useState<SectionContent | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [errorContent, setErrorContent] = useState<string | null>(null);

  // Quiz states
  const [showQuiz, setShowQuiz] = useState(false);
  const [quizData, setQuizData] = useState<QuizData | null>(null);
  const [loadingQuiz, setLoadingQuiz] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState<Record<number, number>>({});
  const [submittedQuestions, setSubmittedQuestions] = useState<Record<number, boolean>>({});
  const [quizFinished, setQuizFinished] = useState(false);
  const [submittingResult, setSubmittingResult] = useState(false);

  // Reset states when moduleId changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setShell(null);
      setLoadingShell(true);
      setActiveSection(null);
      setSectionContent(null);
      setShowQuiz(false);
      setQuizData(null);
      setQuizAnswers({});
      setSubmittedQuestions({});
      setQuizFinished(false);
      setErrorContent(null);
    }, 0);

    async function loadShell() {
      try {
        const data = await getArtifactShell(topicSlug);
        setShell(data);
        if (data.sections.length > 0) {
          setActiveSection(data.sections[0].slug);
        }
      } catch (err) {
        console.error("Error loading artifact shell:", err);
      } finally {
        setLoadingShell(false);
      }
    }
    loadShell();
    return () => clearTimeout(timer);
  }, [moduleId, topicSlug]);

  // Load section content when active section changes
  useEffect(() => {
    if (!activeSection) return;
    const sectionSlug = activeSection;

    const timer = setTimeout(() => {
      setSectionContent(null);
      setLoadingContent(true);
      setErrorContent(null);
      setShowQuiz(false);
      setQuizData(null);
      setQuizAnswers({});
      setSubmittedQuestions({});
      setQuizFinished(false);
    }, 0);

    async function loadContent() {
      try {
        const data = await getSectionContent(topicSlug, sectionSlug, userStyle);
        setSectionContent(data);
      } catch (err) {
        console.error("Error loading section content:", err);
        setErrorContent("Failed to load section content. Please try again.");
      } finally {
        setLoadingContent(false);
      }
    }
    loadContent();
    return () => clearTimeout(timer);
  }, [activeSection, topicSlug, userStyle]);

  const handleStartQuiz = async () => {
    if (!activeSection) return;
    setLoadingQuiz(true);
    try {
      const data = await getSectionQuiz(topicSlug, activeSection);
      setQuizData(data);
      setShowQuiz(true);
    } catch (err) {
      console.error("Error loading quiz:", err);
    } finally {
      setLoadingQuiz(false);
    }
  };

  const handleSelectAnswer = (qIndex: number, optionIndex: number) => {
    if (submittedQuestions[qIndex]) return;
    setQuizAnswers((prev) => ({ ...prev, [qIndex]: optionIndex }));
  };

  const handleSubmitQuestion = (qIndex: number) => {
    if (quizAnswers[qIndex] === undefined) return;
    setSubmittedQuestions((prev) => ({ ...prev, [qIndex]: true }));
  };

  const handleFinishQuiz = async () => {
    if (!quizData) return;
    setQuizFinished(true);
    setSubmittingResult(true);

    let correctCount = 0;
    quizData.questions.forEach((q, idx) => {
      if (quizAnswers[idx] === q.correct_index) {
        correctCount++;
      }
    });

    const scorePercentage = (correctCount / quizData.questions.length) * 100;

    try {
      await submitQuizResult(moduleId, scorePercentage);
      onProgressUpdate();
    } catch (err) {
      console.error("Failed to submit quiz result:", err);
    } finally {
      setSubmittingResult(false);
    }
  };

  const handleMarkComplete = async () => {
    try {
      await completeModule(moduleId);
      onProgressUpdate();
    } catch (err) {
      console.error("Failed to complete module:", err);
    }
  };

  if (loadingShell) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-1/3 bg-zinc-800" />
        <Skeleton className="h-24 w-full bg-zinc-800" />
        <div className="flex gap-4">
          <Skeleton className="h-10 w-24 bg-zinc-800" />
          <Skeleton className="h-10 w-24 bg-zinc-800" />
        </div>
        <Skeleton className="h-64 w-full bg-zinc-800" />
      </div>
    );
  }

  const currentQuizScore = quizData
    ? Math.round(
        (quizData.questions.filter((q, idx) => quizAnswers[idx] === q.correct_index).length /
          quizData.questions.length) *
          100
      )
    : 0;

  return (
    <div className="space-y-6">
      {/* Shell Introduction */}
      <div className="p-5 md:p-6 rounded-xl bg-zinc-900/50 border border-zinc-850 backdrop-blur-sm relative overflow-hidden">
        <div className="absolute right-0 bottom-0 opacity-[0.03] text-zinc-100 font-extrabold select-none pointer-events-none transform translate-y-1/4 translate-x-1/8 text-9xl">
          AI
        </div>
        <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-indigo-400" />
          Module Overview
        </h3>
        <p className="text-zinc-400 text-sm md:text-base leading-relaxed">{shell?.overview}</p>
      </div>

      {/* Section Tabs */}
      {shell && shell.sections.length > 0 && (
        <div className="border-b border-zinc-850">
          <Tabs
            value={activeSection || ""}
            onValueChange={setActiveSection}
            className="w-full overflow-x-auto"
          >
            <TabsList className="bg-transparent border-0 h-auto p-0 flex gap-2 justify-start overflow-x-auto min-w-max pb-2">
              {shell.sections.map((sec, idx) => (
                <TabsTrigger
                  key={sec.slug}
                  value={sec.slug}
                  className={cn(
                    "px-4 py-2 border-b-2 text-xs md:text-sm font-semibold rounded-none cursor-pointer transition-all bg-transparent shadow-none",
                    activeSection === sec.slug
                      ? "border-violet-500 text-violet-400 font-bold"
                      : "border-transparent text-zinc-400 hover:text-zinc-200"
                  )}
                >
                  <span className="opacity-60 mr-1.5">{idx + 1}.</span>
                  {sec.title}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
      )}

      {/* Section Content Area */}
      <div className="min-h-[250px] relative">
        {loadingContent ? (
          <div className="space-y-4 py-6">
            <Skeleton className="h-6 w-3/4 bg-zinc-800" />
            <Skeleton className="h-4 w-full bg-zinc-800" />
            <Skeleton className="h-4 w-full bg-zinc-800" />
            <Skeleton className="h-4 w-2/3 bg-zinc-800" />
            <Skeleton className="h-32 w-full bg-zinc-800 mt-6" />
          </div>
        ) : errorContent ? (
          <div className="flex flex-col items-center justify-center p-8 border border-red-900/30 rounded-xl bg-red-950/10 text-center space-y-3">
            <AlertTriangle className="w-8 h-8 text-red-500" />
            <p className="text-sm text-zinc-300 font-medium">{errorContent}</p>
            <Button
              onClick={() => {
                if (activeSection) {
                  setActiveSection(null);
                  setTimeout(() => setActiveSection(shell?.sections[0]?.slug || null), 50);
                }
              }}
              className="bg-zinc-850 hover:bg-zinc-800 text-xs border border-zinc-700"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" /> Retry
            </Button>
          </div>
        ) : sectionContent ? (
          <div className="space-y-8">
            {/* Warning overlay for degraded view */}
            {sectionContent.degraded && (
              <div className="flex items-start gap-3 p-3.5 rounded-lg border border-amber-900/40 bg-amber-950/15 text-amber-300 text-xs">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Style overlay disabled:</span> Custom content limits reached. Displaying core guide contents.
                </div>
              </div>
            )}

            {/* Custom Overlay indicator for styling */}
            {sectionContent.has_overlay && (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-violet-500/20 bg-violet-650/10 text-violet-400 text-xs font-semibold w-max shadow-sm">
                <Sparkles className="w-3.5 h-3.5" />
                Tailored for {userStyle || "practical"} learning style
              </div>
            )}

            {/* Rendered content */}
            <div className="prose prose-invert max-w-none">
              <MarkdownRenderer content={sectionContent.content} />
            </div>

            <hr className="border-zinc-850" />

            {/* Quiz Interactive / Take Quiz trigger */}
            {!showQuiz ? (
              <div className="p-6 rounded-xl border border-zinc-850 bg-zinc-900/20 flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="space-y-1 text-center md:text-left">
                  <h4 className="font-semibold text-white flex items-center justify-center md:justify-start gap-2">
                    <HelpCircle className="w-4 h-4 text-violet-400" />
                    Knowledge Check
                  </h4>
                  <p className="text-xs text-zinc-400">
                    Take a 5-question multiple choice quiz to test your comprehension.
                  </p>
                </div>
                <Button
                  onClick={handleStartQuiz}
                  disabled={loadingQuiz}
                  className="bg-zinc-900 hover:bg-zinc-850 text-indigo-400 hover:text-indigo-300 border border-zinc-800 font-semibold cursor-pointer shrink-0"
                >
                  {loadingQuiz ? "Loading..." : "Start Section Quiz"}
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            ) : (
              quizData && (
                <Card className="bg-zinc-950/70 border border-zinc-850 text-white rounded-xl shadow-lg">
                  <CardHeader className="border-b border-zinc-900/60 p-5">
                    <div className="flex justify-between items-center">
                      <CardTitle className="text-base font-bold flex items-center gap-2">
                        <Award className="w-5 h-5 text-indigo-400" />
                        Interactive Quiz: {shell?.sections.find((s) => s.slug === activeSection)?.title}
                      </CardTitle>
                      {quizFinished && (
                        <Badge
                          className={cn(
                            "px-2.5 py-1 text-xs",
                            currentQuizScore >= 80
                              ? "bg-green-500/10 border-green-500/30 text-green-400"
                              : "bg-amber-500/10 border-amber-500/30 text-amber-400"
                          )}
                        >
                          Score: {currentQuizScore}%
                        </Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="p-5 space-y-6">
                    {quizData.questions.map((q, qIdx) => {
                      const selectedAnswer = quizAnswers[qIdx];
                      const isSubmitted = submittedQuestions[qIdx];
                      const isCorrect = selectedAnswer === q.correct_index;

                      return (
                        <div key={qIdx} className="space-y-3 pb-6 border-b border-zinc-900/60 last:border-b-0 last:pb-0">
                          <p className="text-sm font-semibold text-zinc-200">
                            <span className="text-indigo-400 mr-1.5">Q{qIdx + 1}.</span>
                            {q.question}
                          </p>

                          <div className="grid grid-cols-1 gap-2">
                            {q.options.map((opt, optIdx) => {
                              const isSelected = selectedAnswer === optIdx;
                              const isThisCorrect = optIdx === q.correct_index;

                              let buttonStyle = "bg-zinc-900/40 border-zinc-850 hover:bg-zinc-900/80 text-zinc-300 hover:text-white";
                              if (isSubmitted) {
                                if (isThisCorrect) {
                                  buttonStyle = "bg-green-600/10 border-green-500/80 text-green-300 font-semibold";
                                } else if (isSelected) {
                                  buttonStyle = "bg-red-650/10 border-red-500/80 text-red-300";
                                } else {
                                  buttonStyle = "bg-zinc-900/20 border-zinc-900/80 text-zinc-500 opacity-60";
                                }
                              } else if (isSelected) {
                                buttonStyle = "bg-indigo-600/10 border-indigo-500 text-white font-semibold shadow-indigo-900/10";
                              }

                              return (
                                <button
                                  key={optIdx}
                                  onClick={() => handleSelectAnswer(qIdx, optIdx)}
                                  disabled={isSubmitted || quizFinished}
                                  className={cn(
                                    "text-left p-3 rounded-lg border text-xs transition-all duration-150 cursor-pointer flex items-center justify-between",
                                    buttonStyle
                                  )}
                                >
                                  <span>{opt}</span>
                                  {isSubmitted && isThisCorrect && (
                                    <CheckCircle className="w-4 h-4 text-green-400 shrink-0" />
                                  )}
                                </button>
                              );
                            })}
                          </div>

                          {/* Submit button per question */}
                          {selectedAnswer !== undefined && !isSubmitted && (
                            <Button
                              onClick={() => handleSubmitQuestion(qIdx)}
                              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-8 px-4"
                            >
                              Check Answer
                            </Button>
                          )}

                          {/* Explanation */}
                          {isSubmitted && (
                            <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-850 text-xs text-zinc-400 mt-2 leading-relaxed">
                              <span className="font-semibold text-zinc-300 block mb-1">
                                {isCorrect ? "✅ Correct!" : "❌ Incorrect."} Explanation:
                              </span>
                              {q.explanation}
                            </div>
                          )}
                        </div>
                      );
                    })}

                    {/* Finalize button */}
                    {!quizFinished && (
                      <div className="flex justify-end pt-2">
                        <Button
                          onClick={handleFinishQuiz}
                          disabled={
                            Object.keys(submittedQuestions).length < quizData.questions.length ||
                            submittingResult
                          }
                          className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold cursor-pointer px-6"
                        >
                          {submittingResult ? "Saving..." : "Submit Quiz Results"}
                          <ArrowRight className="w-4 h-4 ml-1.5" />
                        </Button>
                      </div>
                    )}

                    {/* Result details after completion */}
                    {quizFinished && (
                      <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/30 text-center space-y-3">
                        <CheckCircle className="w-8 h-8 text-green-400 mx-auto animate-bounce" />
                        <h5 className="font-bold text-white text-base">Quiz Completed!</h5>
                        <p className="text-xs text-zinc-400 max-w-md mx-auto">
                          Your score has been submitted to your progress sheet. You scored{" "}
                          <span className="font-semibold text-white">{currentQuizScore}%</span>. Keep
                          it up!
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )
            )}

            {/* Bottom Actions - Mark Module Complete */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-5 rounded-xl border border-zinc-850 bg-zinc-900/10 backdrop-blur-sm">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-violet-600/15 border border-violet-500/25">
                  <BookmarkCheck className="w-5 h-5 text-violet-400" />
                </div>
                <div>
                  <h4 className="font-semibold text-white text-sm">Module Completion</h4>
                  <p className="text-xs text-zinc-400">
                    {isCompleted
                      ? `Completed with mastery of ${masteryScore}%`
                      : "Mark this module as complete to update your curriculum progress profile."}
                  </p>
                </div>
              </div>

              {!isCompleted ? (
                <Button
                  onClick={handleMarkComplete}
                  className="bg-violet-600 hover:bg-violet-500 text-white font-semibold shadow-lg hover:shadow-violet-900/20 transition-all cursor-pointer px-6 w-full sm:w-auto"
                >
                  Mark Module Completed
                </Button>
              ) : (
                <div className="flex items-center gap-1.5 text-green-400 font-bold text-sm bg-green-500/10 px-3 py-1.5 rounded-full border border-green-500/20">
                  <CheckCircle className="w-4 h-4" />
                  Completed
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
