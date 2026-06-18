"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import {
  Brain,
  BookOpen,
  Search,
  ChevronRight,
  Menu,
  X,
  Zap,
  LogOut,
  User,
  BookMarked,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 16);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!dropdownOpen) return;
    const handle = () => setDropdownOpen(false);
    document.addEventListener("click", handle);
    return () => document.removeEventListener("click", handle);
  }, [dropdownOpen]);

  return (
    <header
      className={cn(
        "fixed top-0 inset-x-0 z-50 transition-all duration-300",
        scrolled
          ? "glass border-b border-white/5 shadow-lg shadow-black/20"
          : "bg-transparent"
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="relative">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg group-hover:shadow-indigo-500/40 transition-shadow duration-300">
                <Brain className="w-4 h-4 text-white" />
              </div>
              <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-400 blur-md opacity-0 group-hover:opacity-50 transition-opacity duration-300" />
            </div>
            <span className="font-bold text-lg tracking-tight gradient-text">
              Erudios
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            <NavLink href="/explore" icon={<BookOpen className="w-4 h-4" />}>
              Explore
            </NavLink>
            <NavLink href="/explore?q=" icon={<Search className="w-4 h-4" />}>
              Search
            </NavLink>
          </nav>

          {/* CTA / User */}
          <div className="hidden md:flex items-center gap-3">
            {loading ? (
              <div className="w-8 h-8 rounded-full bg-white/10 animate-pulse" />
            ) : user ? (
              /* Authenticated user */
              <div className="relative">
                <button
                  id="user-menu-button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDropdownOpen((v) => !v);
                  }}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-xl hover:bg-white/5 transition-colors"
                >
                  {user.avatar_url ? (
                    <img
                      src={user.avatar_url}
                      alt={user.name}
                      className="w-7 h-7 rounded-full ring-1 ring-white/20"
                    />
                  ) : (
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-xs font-bold text-white">
                      {user.name.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <span className="text-sm text-foreground/80 max-w-[120px] truncate">
                    {user.name.split(" ")[0]}
                  </span>
                </button>

                {dropdownOpen && (
                  <div
                    className="absolute right-0 top-full mt-2 w-48 glass border border-white/10 rounded-xl shadow-xl shadow-black/30 py-1 z-50 animate-fade-in-up"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="px-3 py-2 border-b border-white/8">
                      <p className="text-xs text-muted-foreground truncate">@{user.username}</p>
                      <p className="text-xs text-indigo-400 mt-0.5 capitalize">
                        {user.level} · {user.learning_style}
                      </p>
                    </div>
                    <Link
                      href="/learn"
                      onClick={() => setDropdownOpen(false)}
                      className="flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-white/5 transition-colors"
                    >
                      <BookMarked className="w-3.5 h-3.5" />
                      My Curricula
                    </Link>
                    <button
                      onClick={() => { logout(); setDropdownOpen(false); }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-white/5 transition-colors"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              /* Guest */
              <>
                <Link href="/auth/login">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-foreground"
                  >
                    Sign in
                  </Button>
                </Link>
                <Link href="/auth/login">
                  <Button
                    size="sm"
                    className="bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 transition-all duration-200"
                  >
                    <Zap className="w-3.5 h-3.5 mr-1.5" />
                    Start Learning
                  </Button>
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden glass border-t border-white/5 animate-fade-in-up">
          <div className="px-4 py-4 space-y-2">
            <MobileNavLink href="/explore" onClick={() => setMobileOpen(false)}>
              Explore Topics
            </MobileNavLink>
            {user ? (
              <>
                <MobileNavLink href="/learn" onClick={() => setMobileOpen(false)}>
                  My Curricula
                </MobileNavLink>
                <button
                  onClick={() => { logout(); setMobileOpen(false); }}
                  className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-foreground/80 hover:text-foreground hover:bg-white/5 transition-all"
                >
                  <ChevronRight className="w-4 h-4 text-indigo-400" />
                  Sign out
                </button>
              </>
            ) : (
              <>
                <MobileNavLink href="/auth/login" onClick={() => setMobileOpen(false)}>
                  Sign In
                </MobileNavLink>
                <Link href="/auth/login" onClick={() => setMobileOpen(false)}>
                  <Button className="w-full mt-2 bg-gradient-to-r from-indigo-600 to-indigo-500 text-white">
                    Start Learning
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

function NavLink({
  href,
  children,
  icon,
}: {
  href: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-all duration-150"
    >
      {icon}
      {children}
    </Link>
  );
}

function MobileNavLink({
  href,
  children,
  onClick,
}: {
  href: string;
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-foreground/80 hover:text-foreground hover:bg-white/5 transition-all"
    >
      <ChevronRight className="w-4 h-4 text-indigo-400" />
      {children}
    </Link>
  );
}

