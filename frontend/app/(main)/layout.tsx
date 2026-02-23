"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "\uD83D\uDCCA" },
  { href: "/conversations", label: "Conversations", icon: "\uD83D\uDCAC" },
  { href: "/pipeline-editor", label: "Pipeline Editor", icon: "\u26A1" },
  { href: "/templates", label: "Templates", icon: "\uD83D\uDCCB" },
];

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const { user, token, isLoading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !token) {
      router.push("/login");
    }
  }, [isLoading, token, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!token) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col" role="complementary">
        {/* Logo */}
        <div className="px-6 py-5 border-b border-gray-800">
          <Link href="/conversations" className="block">
            <h1 className="text-xl font-bold text-gray-100">AgentForge</h1>
            <p className="text-xs text-gray-500 mt-0.5">Multi-Agent Platform</p>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-primary-600/20 text-primary-400"
                    : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div className="px-4 py-4 border-t border-gray-800">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-sm text-gray-300 truncate">
                {user?.display_name || user?.email || "User"}
              </p>
              {user?.email && (
                <p className="text-xs text-gray-500 truncate">{user.email}</p>
              )}
            </div>
            <button
              onClick={logout}
              className="ml-2 px-3 py-1.5 text-xs text-gray-400 hover:text-red-400 hover:bg-gray-800 rounded transition-colors flex-shrink-0"
            >
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {children}
      </main>
    </div>
  );
}
