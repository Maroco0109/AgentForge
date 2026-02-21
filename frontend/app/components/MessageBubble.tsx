interface MessageBubbleProps {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

export default function MessageBubble({ role, content, timestamp }: MessageBubbleProps) {
  const getRelativeTime = (date: Date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return "Just now";
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return date.toLocaleDateString();
  };

  if (role === "system") {
    return (
      <div className="flex justify-center message-enter">
        <div className="text-xs text-gray-500 italic">
          {content}
        </div>
      </div>
    );
  }

  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} message-enter`}>
      <div className={`max-w-md lg:max-w-2xl ${isUser ? "order-1" : "order-2"}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-primary-600 text-white"
              : "bg-gray-800 text-gray-100"
          }`}
        >
          <p className="whitespace-pre-wrap break-words">{content}</p>
        </div>
        <div
          className={`text-xs text-gray-500 mt-1 px-2 ${
            isUser ? "text-right" : "text-left"
          }`}
        >
          {getRelativeTime(timestamp)}
        </div>
      </div>
    </div>
  );
}
