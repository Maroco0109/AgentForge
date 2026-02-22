export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-100">AgentForge</h1>
          <p className="text-sm text-gray-400 mt-2">User-prompt driven multi-agent platform</p>
        </div>
        {children}
      </div>
    </div>
  );
}
