"use client";

import { use } from "react";
import ChatWindow from "@/app/components/ChatWindow";

interface ChatPageProps {
  params: Promise<{ id: string }>;
}

export default function ChatPage({ params }: ChatPageProps) {
  const { id } = use(params);

  return (
    <div className="flex-1 overflow-hidden">
      <ChatWindow conversationId={id} />
    </div>
  );
}
