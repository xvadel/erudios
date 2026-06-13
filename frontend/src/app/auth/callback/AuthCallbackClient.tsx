"use client";

import { useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function AuthCallbackClient() {
  const params = useSearchParams();
  const router = useRouter();

  const handleCallback = useCallback(() => {
    const token = params.get("token");
    if (token) {
      localStorage.setItem("erudios_token", token);
      router.replace("/explore");
    } else {
      router.replace("/auth/login?error=oauth_failed");
    }
  }, [params, router]);

  useEffect(() => {
    handleCallback();
  }, [handleCallback]);

  return (
    <div className="min-h-dvh flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-muted-foreground text-sm">Completing sign-in…</p>
      </div>
    </div>
  );
}
