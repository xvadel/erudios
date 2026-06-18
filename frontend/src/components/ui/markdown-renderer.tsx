"use client";

import React, { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  if (!content) return null;

  // Split by code blocks first to separate text from code
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className={cn("space-y-4 text-zinc-300 leading-relaxed text-sm md:text-base", className)}>
      {parts.map((part, index) => {
        if (part.startsWith("```")) {
          // Extract language and code content
          const match = part.match(/```(\w*)\n([\s\S]*?)```/);
          const lang = match ? match[1] : "";
          const code = match ? match[2].trim() : part.slice(3, -3).trim();
          return <CodeBlock key={index} code={code} language={lang} />;
        } else {
          return <TextBlock key={index} text={part} />;
        }
      })}
    </div>
  );
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy code", err);
    }
  };

  return (
    <div className="relative group rounded-lg overflow-hidden border border-zinc-800 bg-zinc-950 font-mono text-xs md:text-sm my-4 shadow-inner">
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-850 bg-zinc-900/50 text-zinc-400">
        <span className="text-[11px] uppercase tracking-wider font-semibold">{language || "code"}</span>
        <button
          onClick={handleCopy}
          className="p-1 rounded hover:bg-zinc-850 hover:text-white transition-colors cursor-pointer"
          aria-label="Copy code"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-zinc-200">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function TextBlock({ text }: { text: string }) {
  // Split into lines to process block-level elements
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let currentList: React.ReactNode[] = [];

  const flushList = (key: number) => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`ul-${key}`} className="list-disc pl-6 space-y-1.5 my-3 text-zinc-300">
          {currentList}
        </ul>
      );
      currentList = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Headers
    if (trimmed.startsWith("### ")) {
      flushList(i);
      elements.push(
        <h4 key={i} className="text-base md:text-lg font-semibold text-zinc-100 mt-5 mb-2 flex items-center">
          {parseInline(trimmed.slice(4))}
        </h4>
      );
    } else if (trimmed.startsWith("## ")) {
      flushList(i);
      elements.push(
        <h3 key={i} className="text-lg md:text-xl font-bold text-white mt-6 mb-3 border-b border-zinc-900 pb-1 flex items-center">
          {parseInline(trimmed.slice(3))}
        </h3>
      );
    } else if (trimmed.startsWith("# ")) {
      flushList(i);
      elements.push(
        <h2 key={i} className="text-xl md:text-2xl font-extrabold text-white mt-8 mb-4 flex items-center">
          {parseInline(trimmed.slice(2))}
        </h2>
      );
    }
    // Blockquote
    else if (trimmed.startsWith("> ")) {
      flushList(i);
      elements.push(
        <blockquote key={i} className="border-l-4 border-violet-500 pl-4 py-1 italic bg-zinc-950/40 rounded-r text-zinc-400 my-4">
          {parseInline(trimmed.slice(2))}
        </blockquote>
      );
    }
    // Bullet lists
    else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      currentList.push(<li key={`li-${i}`}>{parseInline(trimmed.slice(2))}</li>);
    } else if (trimmed.startsWith("1. ") || /^\d+\.\s/.test(trimmed)) {
      // Treat numbered lists like simple bullets for now or start a clean container
      flushList(i);
      const content = trimmed.replace(/^\d+\.\s/, "");
      elements.push(
        <div key={i} className="flex items-start gap-2.5 my-2">
          <span className="flex items-center justify-center font-bold text-xs text-indigo-400 bg-indigo-950/50 border border-indigo-900/60 rounded-full w-5 h-5 shrink-0 mt-0.5">
            {trimmed.match(/^\d+/)?.[0]}
          </span>
          <p className="flex-1 text-zinc-300">{parseInline(content)}</p>
        </div>
      );
    }
    // Empty lines
    else if (trimmed === "") {
      flushList(i);
    }
    // Regular paragraph text
    else {
      flushList(i);
      elements.push(
        <p key={i} className="my-3 text-zinc-300">
          {parseInline(line)}
        </p>
      );
    }
  }

  // Flush any remaining list items
  flushList(lines.length);

  return <>{elements}</>;
}

function parseInline(text: string): React.ReactNode[] {
  // Process bold (**bold**), italic (*italic*), and inline code (`code`)
  // Regex to match bold, italic, or inline code
  const regex = /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g;
  const parts = text.split(regex);

  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-bold text-white text-zinc-100">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return (
        <em key={index} className="italic text-zinc-200">
          {part.slice(1, -1)}
        </em>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={index}
          className="px-1.5 py-0.5 mx-0.5 rounded font-mono text-xs md:text-sm bg-zinc-900 border border-zinc-800 text-indigo-300 font-semibold"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}
