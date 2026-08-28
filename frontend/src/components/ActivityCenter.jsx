import { useEffect, useState, useRef } from "react";
import { useEventStream, EVENT_TYPES } from "../api/events";

const EVENT_ICONS = {
  [EVENT_TYPES.DOCUMENT_UPLOADED]: { icon: "📤", color: "text-blue-400" },
  [EVENT_TYPES.OCR_STARTED]: { icon: "🔍", color: "text-amber-400" },
  [EVENT_TYPES.OCR_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.CLEANING_STARTED]: { icon: "🧹", color: "text-amber-400" },
  [EVENT_TYPES.CLEANING_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.CHUNKING_STARTED]: { icon: "✂️", color: "text-amber-400" },
  [EVENT_TYPES.CHUNKING_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.EMBEDDING_STARTED]: { icon: "🔢", color: "text-amber-400" },
  [EVENT_TYPES.EMBEDDING_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.ENTITY_EXTRACTION_STARTED]: { icon: "🏷️", color: "text-amber-400" },
  [EVENT_TYPES.ENTITY_EXTRACTION_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.KNOWLEDGE_GRAPH_STARTED]: { icon: "🕸️", color: "text-amber-400" },
  [EVENT_TYPES.KNOWLEDGE_GRAPH_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.INDEXING_STARTED]: { icon: "📚", color: "text-amber-400" },
  [EVENT_TYPES.INDEXING_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.DOCUMENT_PROCESSED]: { icon: "🎉", color: "text-green-400" },
  [EVENT_TYPES.RAG_QUERY_STARTED]: { icon: "🔍", color: "text-purple-400" },
  [EVENT_TYPES.RAG_RETRIEVAL_STARTED]: { icon: "📄", color: "text-purple-400" },
  [EVENT_TYPES.RAG_RETRIEVAL_COMPLETED]: { icon: "📄", color: "text-green-400" },
  [EVENT_TYPES.RAG_GENERATION_STARTED]: { icon: "🤖", color: "text-purple-400" },
  [EVENT_TYPES.RAG_STREAMING]: { icon: "💬", color: "text-blue-400" },
  [EVENT_TYPES.RAG_COMPLETED]: { icon: "✨", color: "text-green-400" },
  [EVENT_TYPES.AGENT_STARTED]: { icon: "🤖", color: "text-amber-400" },
  [EVENT_TYPES.AGENT_PROGRESS]: { icon: "⚙️", color: "text-blue-400" },
  [EVENT_TYPES.AGENT_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.AGENT_ERROR]: { icon: "❌", color: "text-red-400" },
  [EVENT_TYPES.WORKFLOW_STARTED]: { icon: "🚀", color: "text-amber-400" },
  [EVENT_TYPES.WORKFLOW_STEP_STARTED]: { icon: "➡️", color: "text-blue-400" },
  [EVENT_TYPES.WORKFLOW_STEP_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.WORKFLOW_COMPLETED]: { icon: "🎉", color: "text-green-400" },
  [EVENT_TYPES.WORKFLOW_FAILED]: { icon: "❌", color: "text-red-400" },
  [EVENT_TYPES.EXECUTION_STARTED]: { icon: "▶️", color: "text-amber-400" },
  [EVENT_TYPES.EXECUTION_PROGRESS]: { icon: "⚡", color: "text-blue-400" },
  [EVENT_TYPES.EXECUTION_COMPLETED]: { icon: "✅", color: "text-green-400" },
  [EVENT_TYPES.EXECUTION_FAILED]: { icon: "❌", color: "text-red-400" },
  [EVENT_TYPES.RESEARCH_STARTED]: { icon: "🔬", color: "text-purple-400" },
  [EVENT_TYPES.RESEARCH_COMPLETED]: { icon: "📊", color: "text-green-400" },
  [EVENT_TYPES.SYSTEM_ERROR]: { icon: "⚠️", color: "text-red-400" },
};

function getEventDisplay(type) {
  const parts = type.split(":");
  return {
    category: parts[0],
    action: parts.slice(1).join(" ").replace(/_/g, " "),
    ...(EVENT_ICONS[type] || { icon: "📌", color: "text-gray-400" }),
  };
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function EventItem({ event }) {
  const { icon, color, category, action } = getEventDisplay(event.type);
  
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg transition-all duration-300 ${
      event.type.includes(":error") || event.type.includes(":failed") 
        ? "bg-red-900/20 border border-red-800" 
        : event.type.includes(":completed")
        ? "bg-green-900/20 border border-green-800"
        : event.type.includes(":started")
        ? "bg-blue-900/20 border border-blue-800"
        : "bg-slate-800/50 border border-slate-700"
    }`}>
      <span className={`text-xl ${color}`}>{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-white capitalize">{category}</span>
          <span className="text-xs text-slate-500 font-mono">
            {formatTimestamp(event.timestamp)}
          </span>
        </div>
        <p className="text-sm text-slate-300 capitalize mt-0.5">{action}</p>
        {event.data?.message && (
          <p className="text-xs text-slate-400 mt-1 truncate">{event.data.message}</p>
        )}
        {event.data?.document_id && (
          <span className="inline-block mt-1 px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-400">
            Doc: {event.data.document_id}
          </span>
        )}
        {event.data?.agent_name && (
          <span className="inline-block mt-1 px-2 py-0.5 bg-purple-900/50 rounded text-xs text-purple-300">
            Agent: {event.data.agent_name}
          </span>
        )}
        {event.data?.progress !== undefined && (
          <div className="mt-2">
            <div className="w-full bg-slate-700 rounded-full h-1.5">
              <div
                className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${event.data.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ActivityCenter({ workspaceId }) {
  const [filter, setFilter] = useState("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const eventsEndRef = useRef(null);
  
  const { events, isConnected } = useEventStream(workspaceId || 1, {
    maxEvents: 50,
    autoReconnect: true,
  });

  const filteredEvents = events.filter((event) => {
    if (filter === "all") return true;
    if (filter === "documents") return event.type.includes("document") || event.type.includes("pipeline");
    if (filter === "agents") return event.type.includes("agent");
    if (filter === "rag") return event.type.includes("rag");
    if (filter === "workflows") return event.type.includes("workflow") || event.type.includes("execution");
    if (filter === "errors") return event.type.includes("error") || event.type.includes("failed");
    return true;
  });

  const eventCounts = {
    all: events.length,
    documents: events.filter((e) => e.type.includes("document") || e.type.includes("pipeline")).length,
    agents: events.filter((e) => e.type.includes("agent")).length,
    rag: events.filter((e) => e.type.includes("rag")).length,
    workflows: events.filter((e) => e.type.includes("workflow") || e.type.includes("execution")).length,
    errors: events.filter((e) => e.type.includes("error") || e.type.includes("failed")).length,
  };

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-white">AI Activity Center</h3>
            <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`} />
            <span className="text-xs text-slate-500">{isConnected ? "Live" : "Disconnected"}</span>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-slate-600"
              />
              Auto-scroll
            </label>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 overflow-x-auto">
          {[
            { key: "all", label: "All", icon: "📊" },
            { key: "documents", label: "Documents", icon: "📄" },
            { key: "agents", label: "Agents", icon: "🤖" },
            { key: "rag", label: "RAG", icon: "🔍" },
            { key: "workflows", label: "Workflows", icon: "⚡" },
            { key: "errors", label: "Errors", icon: "⚠️" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setFilter(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap transition ${
                filter === tab.key
                  ? "bg-blue-600 text-white"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              {eventCounts[tab.key] > 0 && (
                <span className={`px-1.5 py-0.5 rounded-full text-xs ${
                  filter === tab.key ? "bg-blue-500" : "bg-slate-600"
                }`}>
                  {eventCounts[tab.key]}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Events list */}
      <div className="h-96 overflow-y-auto p-4 space-y-2">
        {filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <span className="text-4xl mb-2">📡</span>
            <p>Waiting for events...</p>
            <p className="text-xs mt-1">Events will appear here in real-time</p>
          </div>
        ) : (
          filteredEvents.map((event, index) => (
            <EventItem key={event.event_id || index} event={event} />
          ))
        )}
        <div ref={eventsEndRef} />
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-slate-700 bg-slate-900/50">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{filteredEvents.length} events</span>
          <span>Last update: {events[0] ? formatTimestamp(events[0].timestamp) : "-"}</span>
        </div>
      </div>
    </div>
  );
}
