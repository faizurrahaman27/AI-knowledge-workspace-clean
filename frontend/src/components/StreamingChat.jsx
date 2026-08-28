import { useState, useEffect, useRef } from "react";
import { useEventStream, EVENT_TYPES } from "../api/events";
import ChunkVisualizer from "./ChunkVisualizer";

export default function StreamingChat({ workspace, document }) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamMessage, setCurrentStreamMessage] = useState("");
  const [streamStage, setStreamStage] = useState(null);
  const [retrievedChunks, setRetrievedChunks] = useState([]);
  const [showChunks, setShowChunks] = useState(true);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const wsRef = useRef(null);

  const { events: ragEvents, isConnected } = useEventStream(
    workspace?.id || 1,
    {
      autoReconnect: true,
      eventTypes: [
        EVENT_TYPES.RAG_QUERY_STARTED,
        EVENT_TYPES.RAG_RETRIEVAL_STARTED,
        EVENT_TYPES.RAG_RETRIEVAL_COMPLETED,
        EVENT_TYPES.RAG_RERANKING_STARTED,
        EVENT_TYPES.RAG_RERANKING_COMPLETED,
        EVENT_TYPES.RAG_GENERATION_STARTED,
        EVENT_TYPES.RAG_STREAMING,
        EVENT_TYPES.RAG_COMPLETED,
      ],
    }
  );

  // Handle RAG events for streaming
  useEffect(() => {
    if (ragEvents.length === 0) return;

    const event = ragEvents[0];

    if (event.type === EVENT_TYPES.RAG_QUERY_STARTED) {
      setStreamStage("Searching...");
      setIsStreaming(true);
    } else if (event.type === EVENT_TYPES.RAG_RETRIEVAL_STARTED) {
      setStreamStage("Finding chunks...");
      setIsLoadingChunks(true);
    } else if (event.type === EVENT_TYPES.RAG_RETRIEVAL_COMPLETED) {
      setStreamStage("Ranking results...");
      setIsLoadingChunks(false);
      if (event.data?.chunks) {
        setRetrievedChunks(event.data.chunks);
      }
    } else if (event.type === EVENT_TYPES.RAG_RERANKING_STARTED) {
      setStreamStage("Reranking...");
    } else if (event.type === EVENT_TYPES.RAG_RERANKING_COMPLETED) {
      setStreamStage("Generating response...");
    } else if (event.type === EVENT_TYPES.RAG_GENERATION_STARTED) {
      setStreamStage("Thinking...");
      setCurrentStreamMessage("");
    } else if (event.type === EVENT_TYPES.RAG_STREAMING) {
      setCurrentStreamMessage((prev) => prev + (event.data?.content || ""));
    } else if (event.type === EVENT_TYPES.RAG_COMPLETED) {
      setStreamStage(null);
      setIsStreaming(false);
      
      // Add final message to history
      if (event.data?.response) {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            role: "assistant",
            content: event.data.response,
            chunks: retrievedChunks,
            citations: event.data.citations,
            timestamp: new Date().toISOString(),
          },
        ]);
        setCurrentStreamMessage("");
        setRetrievedChunks([]);
      }
    }
  }, [ragEvents]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStreamMessage]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || isStreaming) return;

    const userQuery = query;
    setQuery("");
    
    // Add user message
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        role: "user",
        content: userQuery,
        timestamp: new Date().toISOString(),
      },
    ]);

    setIsStreaming(true);
    setStreamStage("Searching...");
    setCurrentStreamMessage("");

    try {
      // Call the chat API
      const response = await fetch("/api/chat/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          message: userQuery,
          workspace_id: workspace?.id,
          document_id: document?.id,
        }),
      });

      if (!response.ok) throw new Error("Chat request failed");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = "";

      setStreamStage("Generating...");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        fullResponse += chunk;
        setCurrentStreamMessage(fullResponse);
      }

      // Add assistant message
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: "assistant",
          content: fullResponse,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
          isError: true,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsStreaming(false);
      setStreamStage(null);
      setCurrentStreamMessage("");
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-white">AI Assistant</h3>
          <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`} />
        </div>
        {isStreaming && streamStage && (
          <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-xs animate-pulse">
            {streamStage}
          </span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <span className="text-4xl mb-2">💬</span>
            <p>Ask me anything about your documents</p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Streaming message */}
        {isStreaming && currentStreamMessage && (
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div className="flex items-start gap-3">
              <span className="text-2xl">🤖</span>
              <div className="flex-1">
                <p className="text-white whitespace-pre-wrap">{currentStreamMessage}</p>
                <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-1" />
              </div>
            </div>
          </div>
        )}

        {/* Retrieved chunks during streaming */}
        {isStreaming && retrievedChunks.length > 0 && (
          <div className="mt-4">
            <button
              onClick={() => setShowChunks(!showChunks)}
              className="flex items-center gap-2 text-sm text-slate-400 hover:text-white mb-2"
            >
              <span>{showChunks ? "▼" : "▶"}</span>
              Retrieved Chunks ({retrievedChunks.length})
            </button>
            {showChunks && (
              <ChunkVisualizer chunks={retrievedChunks} isLoading={isLoadingChunks} />
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question..."
            disabled={isStreaming}
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!query.trim() || isStreaming}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-medium text-white transition"
          >
            {isStreaming ? "..." : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <span className={`text-2xl ${isUser ? "order-2" : "order-1"}`}>
        {isUser ? "👤" : "🤖"}
      </span>
      <div className={`max-w-[80%] ${isUser ? "order-1" : "order-2"}`}>
        <div
          className={`rounded-xl p-4 ${
            isUser
              ? "bg-blue-600 text-white"
              : message.isError
              ? "bg-red-900/50 border border-red-800"
              : "bg-slate-800 border border-slate-700"
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.citations.map((citation, i) => (
              <div
                key={i}
                className="text-xs bg-slate-800/50 rounded px-2 py-1 text-slate-400"
              >
                [{i + 1}] {citation.source} - Page {citation.page}
              </div>
            ))}
          </div>
        )}

        {/* Retained chunks */}
        {message.chunks && message.chunks.length > 0 && (
          <details className="mt-2">
            <summary className="text-xs text-slate-400 cursor-pointer hover:text-white">
              View {message.chunks.length} sources
            </summary>
            <div className="mt-2">
              <ChunkVisualizer chunks={message.chunks} />
            </div>
          </details>
        )}

        <p className="text-xs text-slate-500 mt-1">
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
