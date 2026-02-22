import type { Metadata } from "next";
import "./globals.css";
import { AuthProviderWrapper } from "@/lib/auth-provider-wrapper";

export const metadata: Metadata = {
  title: "AgentForge",
  description: "User-prompt driven multi-agent platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="dark">
      <body className="antialiased">
        <AuthProviderWrapper>
          {children}
        </AuthProviderWrapper>
      </body>
    </html>
  );
}
