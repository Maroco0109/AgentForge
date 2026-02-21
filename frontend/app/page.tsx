import ChatWindow from "./components/ChatWindow";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950 flex flex-col">
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-100">AgentForge</h1>
        <p className="text-sm text-gray-400 mt-1">User-prompt driven multi-agent platform</p>
      </header>
      <div className="flex-1 overflow-hidden">
        <ChatWindow />
      </div>
    </main>
  );
}
