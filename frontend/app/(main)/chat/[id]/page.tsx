"use client";

import ChatWindow from "@/app/components/ChatWindow";

interface ChatPageProps {
  params: { id: string };
}

export default function ChatPage({ params }: ChatPageProps) {
  return (
    <div className="flex-1 overflow-hidden">
      <ChatWindow conversationId={params.id} />
    </div>
  );
}
