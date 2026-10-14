"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Sparkles, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";

const POPULAR_TOPICS = [
  "RAG", "LLMs", "Transformers", "MLOps", "Agentic AI", "Fine-Tuning",
  "Vector Databases", "Prompt Engineering",
];

export function HeroSection() {
  const [query, setQuery] = useState("");
  const router = useRouter();

  const handleSearch = (q: string) => {
    if (!q.trim()) return;
    router.push(`/explore?q=${encodeURIComponent(q.trim())}`);
  };

  return (
    <section className="relative pt-32 pb-24 px-4 overflow-hidden">
      {/* Background orbs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-indigo-600/10 blur-3xl animate-float" />
        <div className="absolute top-1/3 right-1/4 w-72 h-72 rounded-full bg-cyan-400/8 blur-3xl animate-float [animation-delay:1.5s]" />
        <div className="absolute bottom-1/4 left-1/2 w-64 h-64 rounded-full bg-violet-500/8 blur-3xl animate-float [animation-delay:3s]" />
      </div>

      <div className="relative max-w-4xl mx-auto text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass border border-indigo-500/20 text-sm text-indigo-300 mb-8 animate-fade-in-up">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Open-source AI Learning Platform</span>
        </div>

        {/* Headline */}
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tighter mb-6 animate-fade-in-up stagger-1">
          Stop Searching.{" "}
          <span className="gradient-text">Start Learning.</span>
        </h1>

        {/* Sub-headline */}
        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed animate-fade-in-up stagger-2">
          Erudios builds a clear, ordered learning path for any AI/ML topic.
          Curated resources, personalized curriculum, and always answers{" "}
          <em className="text-foreground/80 not-italic font-medium">
            "what should I learn next?"
          </em>
        </p>

        {/* Search bar */}
        <div className="flex flex-col sm:flex-row gap-3 max-w-xl mx-auto mb-8 animate-fade-in-up stagger-3">
          <div className="relative flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch(query)}
              placeholder="e.g. RAG, Transformers, MLOps…"
              className="w-full h-12 pl-4 pr-4 rounded-xl bg-white/5 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-indigo-500/50 focus:bg-white/8 transition-all duration-200"
            />
          </div>
          <Button
            onClick={() => handleSearch(query)}
            size="lg"
            className="h-12 px-6 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50 transition-all duration-200 shrink-0"
          >
            Build My Path
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>

        {/* Popular topics */}
        <div className="flex flex-wrap justify-center gap-2 animate-fade-in-up stagger-4">
          <span className="text-xs text-muted-foreground mr-1 self-center">Popular:</span>
          {POPULAR_TOPICS.map((t) => (
            <button
              key={t}
              onClick={() => handleSearch(t)}
              className="px-3 py-1 text-xs rounded-full glass border border-white/8 text-foreground/70 hover:text-foreground hover:border-indigo-500/40 hover:bg-indigo-500/10 transition-all duration-150"
            >
              {t}
            </button>
          ))}
        </div>

        {/* Scroll indicator */}
        <div className="mt-20 flex justify-center animate-bounce">
          <ChevronDown className="w-5 h-5 text-muted-foreground/50" />
        </div>
      </div>
    </section>
  );
}
