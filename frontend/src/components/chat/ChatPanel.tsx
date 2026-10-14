"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  MessageSquare,
  X,
  Send,
  Bot,
  User,
  Loader2,
  BookOpen,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/hooks/use-toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ChatSource {
  index: number;
  title: string;
  url: string;
  score: number;
  source_type: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: ChatSource[];
  isStreaming?: boolean;
}

interface ChatPanelProps {
  topicSlug: string;
  topicName: string;
  className?: string;
}

export function ChatPanel({ topicSlug, topicName, className }: ChatPanelProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  const createSession = useCallback(async () => {
    if (!user) return;
    setIsCreatingSession(true);
    try {
      const token = localStorage.getItem("erudios_token");
      const res = await fetch(`${API_BASE}/api/v1/chat/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ topic_slug: topicSlug }),
      });
      if (!res.ok) throw new Error("Failed to create session");
      const session = await res.json();
      setSessionId(session.id);
    } catch {
      toast({ title: "Couldn't start chat session", variant: "destructive" });
    } finally {
      setIsCreatingSession(false);
    }
  }, [user, topicSlug, toast]);

  // Create session when panel first opens
  useEffect(() => {
    if (isOpen && !sessionId && user) {
      createSession();
    }
  }, [isOpen, sessionId, user, createSession]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || !sessionId) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      sources: [],
    };
    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      sources: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setIsStreaming(true);

    try {
      const token = localStorage.getItem("erudios_token");
      const res = await fetch(
        `${API_BASE}/api/v1/chat/sessions/${sessionId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ content: trimmed }),
        }
      );

      if (!res.ok || !res.body) throw new Error("Stream failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, content: fullContent, isStreaming: false }
                  : m
              )
            );
            break;
          }
          fullContent += payload;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id ? { ...m, content: fullContent } : m
            )
          );
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id
            ? {
                ...m,
                content: "Sorry, something went wrong. Please try again.",
                isStreaming: false,
              }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!user) return null;

  return (
    <>
      {/* Floating toggle button */}
      <button
        id="chat-panel-toggle"
        onClick={() => setIsOpen((o) => !o)}
        className={cn(
          "fixed bottom-6 right-6 z-40 flex items-center justify-center w-14 h-14 rounded-full",
          "bg-gradient-to-br from-indigo-600 to-violet-600 shadow-xl shadow-indigo-500/30",
          "hover:scale-105 active:scale-95 transition-transform",
          className
        )}
        aria-label="Toggle AI Tutor"
      >
        {isOpen ? (
          <X className="w-5 h-5 text-white" />
        ) : (
          <MessageSquare className="w-5 h-5 text-white" />
        )}
      </button>

      {/* Chat panel */}
      <div
        className={cn(
          "fixed bottom-24 right-6 z-40 w-[min(420px,calc(100vw-3rem))] h-[min(600px,calc(100dvh-8rem))]",
          "glass border border-white/10 rounded-2xl shadow-2xl flex flex-col",
          "transition-all duration-300 origin-bottom-right",
          isOpen
            ? "opacity-100 scale-100 pointer-events-auto"
            : "opacity-0 scale-95 pointer-events-none"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold">AI Tutor</p>
              <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                {topicName}
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin">
          {isCreatingSession && (
            <div className="flex items-center justify-center gap-2 text-muted-foreground text-sm py-8">
              <Loader2 className="w-4 h-4 animate-spin" />
              Starting session…
            </div>
          )}

          {!isCreatingSession && messages.length === 0 && (
            <div className="flex flex-col items-center gap-3 text-center py-8">
              <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <p className="text-sm font-medium">Ask me anything about</p>
                <p className="text-sm text-indigo-400 font-semibold">{topicName}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  I'll use curated resources to answer your questions.
                </p>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex gap-2.5",
                msg.role === "user" ? "flex-row-reverse" : "flex-row"
              )}
            >
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                  msg.role === "user"
                    ? "bg-indigo-600"
                    : "bg-gradient-to-br from-violet-600 to-indigo-600"
                )}
              >
                {msg.role === "user" ? (
                  <User className="w-3.5 h-3.5 text-white" />
                ) : (
                  <Bot className="w-3.5 h-3.5 text-white" />
                )}
              </div>

              <div
                className={cn(
                  "max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                  msg.role === "user"
                    ? "bg-indigo-600 text-white rounded-tr-sm"
                    : "bg-white/5 border border-white/8 text-foreground rounded-tl-sm"
                )}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.isStreaming && (
                  <span className="inline-block w-1.5 h-4 bg-current opacity-70 animate-pulse ml-0.5" />
                )}

                {/* Sources */}
                {msg.sources.length > 0 && (
                  <div className="mt-2.5 pt-2.5 border-t border-white/10 space-y-1">
                    <p className="text-xs text-muted-foreground font-medium">Sources</p>
                    {msg.sources.map((src) => (
                      <a
                        key={src.index}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        <ExternalLink className="w-3 h-3 shrink-0" />
                        <span className="line-clamp-1">[{src.index}] {src.title}</span>
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-3 py-3 border-t border-white/10 shrink-0">
          <div className="flex items-end gap-2 bg-white/5 border border-white/10 rounded-xl px-3 py-2 focus-within:border-indigo-500/50 transition-colors">
            <textarea
              ref={inputRef}
              id="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question…"
              rows={1}
              disabled={isStreaming || isCreatingSession}
              className="flex-1 bg-transparent text-sm resize-none outline-none placeholder:text-muted-foreground max-h-32 disabled:opacity-50"
              style={{ minHeight: "1.5rem" }}
            />
            <button
              id="chat-send-btn"
              onClick={sendMessage}
              disabled={!input.trim() || isStreaming || isCreatingSession}
              className={cn(
                "shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all",
                "bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed"
              )}
            >
              {isStreaming ? (
                <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5 text-white" />
              )}
            </button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-1.5">
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    </>
  );
}
