"use client";

import { AuthProvider } from "@/lib/auth-context";

export function AuthProviderWrapper({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
