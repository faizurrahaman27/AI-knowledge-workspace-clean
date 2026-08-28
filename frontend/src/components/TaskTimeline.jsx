import { useState, useEffect } from "react";
import { useEventStream, EVENT_TYPES } from "../api/events";

function formatTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function TimelineEvent({ event, isFirst, isLast }) {
  const isError = event.type.includes(":error") || event.type.includes(":failed");
  const isCompleted = event.type.includes(":completed");
  const isStarted = event.type.includes(":started");

  return (
    <div className="relative flex gap-4">
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <div
          className={`w-4 h-4 rounded-full border-2 z-10 ${
            isError
              ? "bg-red-500 border-red-400"
              : isCompleted
              ? "bg-green-500 border-green-400"
              : isStarted
              ? "bg-blue-500 border-blue-400"
              : "bg-slate-600 border-slate-500"
          }`}
        />
        {!isLast && (
          <div
            className={`w-0.5 flex-1 ${
              isCompleted ? "bg-green-500" : "bg-slate-600"
            }`}
          />
        )}
      </div>

      {/* Event content */}
      <div
        className={`flex-1 pb-6 ${isError ? "text-red-400" : isCompleted ? "text-green-400" : "text-slate-300"}`}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-medium text-white">
              {event.type
                .replace(/_/g, " ")
                .replace(/:/g, " ")
                .split(" ")
                .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                .join(" ")}
            </p>
            {event.data?.message && (
              <p className="text-sm text-slate-400 mt-0.5">{event.data.message}</p>
            )}
            {event.data?.agent_name && (
              <span className="inline-block mt-1 px-2 py-0.5 bg-purple-900/50 rounded text-xs text-purple-300">
                {event.data.agent_name}
              </span>
            )}
            {event.data?.document_id && (
              <span className="inline-block mt-1 ml-2 px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-400">
                Doc: {event.data.document_id}
              </span>
            )}
          </div>
          <span className="text-xs text-slate-500 font-mono whitespace-nowrap">
            {formatTime(event.timestamp)}
          </span>
        </div>

        {/* Progress bar for running events */}
        {event.data?.progress !== undefined && (
          <div className="mt-2 w-48">
            <div className="w-full bg-slate-700 rounded-full h-1">
              <div
                className="bg-blue-500 h-1 rounded-full transition-all duration-300"
                style={{ width: `${event.data.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error details */}
        {isError && event.data?.error && (
          <div className="mt-2 p-2 bg-red-900/30 rounded-lg">
            <p className="text-xs text-red-400">{event.data.error}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function TaskTimeline({ workspaceId, maxEvents = 50 }) {
  const [events, setEvents] = useState([]);
  const [filter, setFilter] = useState("all");
  const [isPaused, setIsPaused] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  
  const { events: newEvents, isConnected } = useEventStream(workspaceId || 1, {
    maxEvents: maxEvents,
    eventTypes: [],
  });

  useEffect(() => {
    if (!isPaused && newEvents.length > 0) {
      setEvents(newEvents);
    }
  }, [newEvents, isPaused]);

  const filteredEvents = events.filter((event) => {
    // Apply category filter
    if (filter !== "all") {
      if (filter === "documents" && !event.type.includes("document") && !event.type.includes("pipeline")) {
        return false;
      }
      if (filter === "agents" && !event.type.includes("agent")) {
        return false;
      }
      if (filter === "rag" && !event.type.includes("rag")) {
        return false;
      }
      if (filter === "workflows" && !event.type.includes("workflow") && !event.type.includes("execution")) {
        return false;
      }
      if (filter === "errors" && !event.type.includes("error") && !event.type.includes("failed")) {
        return false;
      }
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        event.type.toLowerCase().includes(query) ||
        event.data?.message?.toLowerCase().includes(query) ||
        event.data?.agent_name?.toLowerCase().includes(query)
      );
    }

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

  const clearEvents = () => {
    setEvents([]);
  };

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-white">Task Timeline</h3>
            <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`} />
            <span className="text-xs text-slate-500">
              {events.length} events
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                isPaused
                  ? "bg-amber-500/20 text-amber-400 hover:bg-amber-500/30"
                  : "bg-blue-500/20 text-blue-400 hover:bg-blue-500/30"
              }`}
            >
              {isPaused ? "▶ Resume" : "⏸ Pause"}
            </button>
            <button
              onClick={clearEvents}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-700 text-slate-300 hover:bg-slate-600 transition"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search events..."
            className="w-full bg-slate-700 border border-slate-600 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 overflow-x-auto pb-1">
          {[
            { key: "all", label: "All", icon: "📊" },
            { key: "documents", label: "Docs", icon: "📄" },
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

      {/* Timeline */}
      <div className="p-4 max-h-96 overflow-y-auto">
        {filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <span className="text-4xl mb-2">📋</span>
            <p>No events recorded</p>
            <p className="text-xs mt-1">Events will appear here as they happen</p>
          </div>
        ) : (
          <div className="relative">
            {filteredEvents.map((event, index) => (
              <TimelineEvent
                key={event.event_id || index}
                event={event}
                isFirst={index === 0}
                isLast={index === filteredEvents.length - 1}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-slate-700 bg-slate-900/50">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>
            Showing {filteredEvents.length} of {events.length} events
          </span>
          {events.length > 0 && (
            <span>
              Started: {formatTime(events[events.length - 1]?.timestamp)} -{" "}
              Latest: {formatTime(events[0]?.timestamp)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
