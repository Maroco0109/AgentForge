"use client";

import { useState, useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

function formatDiscussionMessage(data: Record<string, unknown>): string {
  const type = data.type as string;
  const content = (data.content as string) || "";

  if (type === "clarification") {
    const questions = (data.questions as string[]) || [];
    return `${content}\n\n${questions.map((q, i) => `${i + 1}. ${q}`).join("\n")}`;
  }

  if (type === "designs_presented") {
    const designs = (data.designs as Array<Record<string, unknown>>) || [];
    const designTexts = designs.map((d, i) => {
      const name = d.name as string;
      const desc = d.description as string;
      const complexity = d.complexity as string;
      const cost = d.estimated_cost as string;
      const recommended = d.recommended ? " ⭐ Recommended" : "";
      const pros = (d.pros as string[]) || [];
      const cons = (d.cons as string[]) || [];
      return (
        `**${i + 1}. ${name}${recommended}**\n` +
        `${desc}\n` +
        `Complexity: ${complexity} | Cost: ${cost}\n` +
        `Pros: ${pros.join(", ")}\n` +
        `Cons: ${cons.join(", ")}`
      );
    });
    return `${content}\n\n${designTexts.join("\n\n")}`;
  }

  if (type === "critique_complete") {
    const critiques = (data.critiques as Array<Record<string, unknown>>) || [];
    const critiqueTexts = critiques.map((c) => {
      const designName = c.design_name as string;
      const score = c.overall_score as number;
      return `**${designName}** (Score: ${score}/10)`;
    });
    return `${content}\n\n${critiqueTexts.join("\n")}`;
  }

  return content;
}

function openDesignInEditor(designs: Array<Record<string, unknown>>) {
  // Find the recommended design, or use the first one
  const recommended = designs.find((d) => d.recommended) || designs[0];
  if (!recommended) return;

  // Find the pipeline editor container and call loadDesign
  const editorEl = document.querySelector("[data-pipeline-editor]") as
    | (HTMLDivElement & {
        loadDesign?: (design: Record<string, unknown>) => void;
      })
    | null;

  if (editorEl?.loadDesign) {
    editorEl.loadDesign(recommended as Record<string, unknown>);

    // Open the editor panel if closed
    const toggleBtn = document.querySelector(
      'button[title="Open Pipeline Editor"]'
    ) as HTMLButtonElement | null;
    if (toggleBtn) toggleBtn.click();
  }
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getToken = (): string => {
    return typeof window !== "undefined" ? localStorage.getItem("access_token") || "" : "";
  };

  const createConversation = async (): Promise<string | null> => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = getToken();
    if (!token) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          content: "Authentication required. Please log in first.",
          timestamp: new Date(),
        },
      ]);
      return null;
    }

    try {
      const response = await fetch(`${apiBase}/api/v1/conversations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title: "New Conversation" }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create conversation: ${response.status}`);
      }

      const data = await response.json();
      return data.id;
    } catch (error) {
      console.error("Failed to create conversation:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          content: "Failed to start conversation. Please check your connection.",
          timestamp: new Date(),
        },
      ]);
      return null;
    }
  };

  const connectWebSocket = (convId: string) => {
    const wsBase = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const token = getToken();
    const wsUrl = `${wsBase}/api/v1/ws/chat/${convId}${token ? `?token=${token}` : ""}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      const isReconnect = reconnectAttemptsRef.current > 0;
      reconnectAttemptsRef.current = 0;
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          content: isReconnect ? "Reconnected to AgentForge" : "Connected to AgentForge",
          timestamp: new Date(),
        },
      ]);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const type = data.type as string;

        switch (type) {
          case "user_message_received":
            // Already shown in UI, skip
            break;

          case "clarification":
          case "critique_complete":
          case "plan_generated": {
            setIsTyping(false);
            const formatted = formatDiscussionMessage(data);
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "assistant",
                content: formatted,
                timestamp: new Date(),
                metadata: data,
              },
            ]);
            break;
          }

          case "designs_presented": {
            setIsTyping(false);
            const formatted = formatDiscussionMessage(data);
            const designs = (data.designs as Array<Record<string, unknown>>) || [];
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "assistant",
                content: formatted,
                timestamp: new Date(),
                metadata: data,
              },
              ...(designs.length > 0
                ? [
                    {
                      id: crypto.randomUUID(),
                      role: "system" as const,
                      content: "__open_in_editor__",
                      timestamp: new Date(),
                      metadata: { designs },
                    },
                  ]
                : []),
            ]);
            break;
          }

          case "pipeline_started":
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "system",
                content: `Pipeline started: ${data.design_name || "Running"} (${data.agent_count || 0} agents)`,
                timestamp: new Date(),
              },
            ]);
            break;

          case "agent_completed":
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "system",
                content: `Agent "${data.agent_name}" completed (${data.duration || 0}s)`,
                timestamp: new Date(),
              },
            ]);
            break;

          case "pipeline_result": {
            setIsTyping(false);
            const result = data.result || {};
            const output = result.output || data.content || "Pipeline completed.";
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "assistant",
                content: output,
                timestamp: new Date(),
                metadata: { pipeline_result: result },
              },
            ]);
            break;
          }

          case "pipeline_failed":
            setIsTyping(false);
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "system",
                content: `Pipeline failed: ${data.reason || "Unknown error"}`,
                timestamp: new Date(),
              },
            ]);
            break;

          case "security_warning":
          case "error":
            setIsTyping(false);
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "system",
                content: data.content || "An error occurred.",
                timestamp: new Date(),
              },
            ]);
            break;

          case "assistant_message":
          default:
            setIsTyping(false);
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "assistant",
                content: data.content || data.message || JSON.stringify(data),
                timestamp: new Date(),
              },
            ]);
            break;
        }
      } catch {
        console.error("Failed to parse WebSocket message:", event.data);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
      setIsTyping(false);
      wsRef.current = null;

      // Exponential backoff reconnect
      const backoffDelay = Math.min(30000, 1000 * Math.pow(2, reconnectAttemptsRef.current));
      reconnectAttemptsRef.current += 1;

      reconnectTimeoutRef.current = setTimeout(() => {
        console.log(`Reconnecting (attempt ${reconnectAttemptsRef.current})...`);
        connectWebSocket(convId);
      }, backoffDelay);
    };

    wsRef.current = ws;
  };

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      const convId = await createConversation();
      if (cancelled || !convId) return;
      setConversationId(convId);
      connectWebSocket(convId);
    };

    init();

    return () => {
      cancelled = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputValue.trim() || !isConnected || !wsRef.current) {
      return;
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    wsRef.current.send(
      JSON.stringify({
        content: inputValue,
        conversation_id: conversationId,
      })
    );

    setInputValue("");
  };

  const renderMessage = (message: Message) => {
    // Special "Open in Editor" button message
    if (message.content === "__open_in_editor__" && message.metadata?.designs) {
      return (
        <div key={message.id} className="flex justify-center py-1">
          <button
            onClick={() =>
              openDesignInEditor(
                message.metadata!.designs as Array<Record<string, unknown>>
              )
            }
            className="px-4 py-1.5 bg-primary-600/20 hover:bg-primary-600/40 text-primary-400 text-sm rounded-full border border-primary-600/30 transition-colors"
          >
            Open in Pipeline Editor
          </button>
        </div>
      );
    }

    return (
      <MessageBubble
        key={message.id}
        role={message.role}
        content={message.content}
        timestamp={message.timestamp}
      />
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.map(renderMessage)}

        {isTyping && (
          <div className="flex items-start space-x-2">
            <div className="bg-gray-800 rounded-2xl px-4 py-3 max-w-xs">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-800 bg-gray-900 px-4 py-4">
        <form onSubmit={handleSend} className="flex items-center space-x-2">
          <div className="flex items-center space-x-2 flex-1">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}
                 title={isConnected ? 'Connected' : 'Disconnected'} />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 bg-gray-800 text-gray-100 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              disabled={!isConnected}
            />
          </div>
          <button
            type="submit"
            disabled={!isConnected || !inputValue.trim()}
            className="bg-primary-600 hover:bg-primary-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg font-medium transition-colors"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
