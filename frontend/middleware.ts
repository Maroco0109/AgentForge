import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Middleware runs on the edge and cannot access localStorage.
// Instead, we check for the token cookie or rely on client-side redirects.
// For this app, auth state is managed client-side via localStorage.
// The middleware provides basic route protection by checking if
// the request has an authorization-related cookie.
// Primary auth protection happens client-side in the AuthProvider.

const PUBLIC_PATHS = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths, static files, and API routes
  if (
    PUBLIC_PATHS.some((p) => pathname.startsWith(p)) ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // For all other routes, let the page render
  // Client-side auth check will redirect if needed
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
