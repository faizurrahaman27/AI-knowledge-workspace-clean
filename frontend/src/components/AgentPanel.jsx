import { useState, useEffect } from "react";
import { useEventStream, EVENT_TYPES } from "../api/events";

const AGENT_TYPES = {
  research: { icon: "🔬", label: "Research Agent", color: "blue" },
  knowledge: { icon: "📚", label: "Knowledge Agent", color: "purple" },
  memory: { icon: "🧠", label: "Memory Agent", color: "amber" },
  reasoning: { icon: "💭", label: "Reasoning Agent", color: "green" },
  execution: { icon: "⚡", label: "Execution Agent", color: "red" },
  citation: { icon: "📖", label: "Citation Agent", color: "cyan" },
  orchestrator: { icon: "🎭", label: "Orchestrator", color: "pink" },
  planner: { icon: "📋", label: "Planner Agent", color: "indigo" },
  search: { icon: "🔍", label: "Search Agent", color: "teal" },
  verification: { icon: "✓", label: "Verification Agent", color: "emerald" },
};

function AgentCard({ agent }) {
  const elapsed = agent.startedAt
    ? Math.floor((Date.now() - new Date(agent.startedAt).getTime()) / 1000)
    : 0;
  
  const elapsedStr = elapsed > 60
    ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
    : `${elapsed}s`;

  const type = agent.name?.toLowerCase().includes("research")
    ? "research"
    : agent.name?.toLowerCase().includes("knowledge")
    ? "knowledge"
    : agent.name?.toLowerCase().includes("memory")
    ? "memory"
    : agent.name?.toLowerCase().includes("reasoning")
    ? "reasoning"
    : agent.name?.toLowerCase().includes("execution")
    ? "execution"
    : agent.name?.toLowerCase().includes("citation")
    ? "citation"
    : agent.name?.toLowerCase().includes("orchestrator")
    ? "orchestrator"
    : agent.name?.toLowerCase().includes("planner")
    ? "planner"
    : agent.name?.toLowerCase().includes("search")
    ? "search"
    : agent.name?.toLowerCase().includes("verification")
    ? "verification"
    : "execution";

  const agentType = AGENT_TYPES[type] || AGENT_TYPES.execution;

  return (
    <div className={`p-4 rounded-xl border transition-all ${
      agent.status === "completed"
        ? "bg-green-900/20 border-green-800"
        : agent.status === "error"
        ? "bg-red-900/20 border-red-800"
        : agent.status === "running"
        ? "bg-blue-900/20 border-blue-800 animate-pulse-subtle"
        : "bg-slate-800/50 border-slate-700"
    }`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{agentType.icon}</span>
          <div>
            <h4 className="font-medium text-white">{agent.name}</h4>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              agent.status === "completed"
                ? "bg-green-500/20 text-green-400"
                : agent.status === "error"
                ? "bg-red-500/20 text-red-400"
                : agent.status === "running"
                ? "bg-blue-500/20 text-blue-400"
                : "bg-slate-600 text-slate-300"
            }`}>
              {agent.status}
            </span>
          </div>
        </div>
        {agent.status === "running" && (
          <span className="text-xs text-slate-400 font-mono">{elapsedStr}</span>
        )}
      </div>

      <p className="text-sm text-slate-300 mb-3">{agent.task}</p>

      {agent.progress !== undefined && agent.progress !== null && (
        <div className="mb-2">
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>Progress</span>
            <span>{Math.round(agent.progress)}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                agent.status === "completed"
                  ? "bg-green-500"
                  : "bg-blue-500"
              }`}
              style={{ width: `${Math.min(100, Math.max(0, agent.progress))}%` }}
            />
          </div>
        </div>
      )}

      {agent.error && (
        <div className="mt-2 p-2 bg-red-900/30 rounded-lg">
          <p className="text-xs text-red-400">{agent.error}</p>
        </div>
      )}
    </div>
  );
}

export default function AgentPanel({ workspaceId }) {
  const [agents, setAgents] = useState({});
  const [filter, setFilter] = useState("all");
  const { events, isConnected } = useEventStream(workspaceId || 1, {
    maxEvents: 200,
    eventTypes: [
      EVENT_TYPES.AGENT_STARTED,
      EVENT_TYPES.AGENT_PROGRESS,
      EVENT_TYPES.AGENT_COMPLETED,
      EVENT_TYPES.AGENT_ERROR,
      EVENT_TYPES.WORKFLOW_STARTED,
      EVENT_TYPES.WORKFLOW_STEP_STARTED,
      EVENT_TYPES.WORKFLOW_STEP_COMPLETED,
      EVENT_TYPES.WORKFLOW_COMPLETED,
    ],
  });

  useEffect(() => {
    const newAgents = { ...agents };
    
    events.forEach((event) => {
      const agentId = event.agent_id || event.data?.agent_id || event.workflow_id;
      if (!agentId) return;

      if (event.type === EVENT_TYPES.AGENT_STARTED || event.type === EVENT_TYPES.WORKFLOW_STARTED) {
        newAgents[agentId] = {
          id: agentId,
          name: event.data?.agent_name || event.data?.workflow_name || event.workflow_id || agentId,
          status: "running",
          task: event.data?.task || event.data?.message || "Starting...",
          progress: 0,
          startedAt: event.timestamp,
        };
      } else if (event.type === EVENT_TYPES.AGENT_PROGRESS || event.type === EVENT_TYPES.WORKFLOW_STEP_STARTED) {
        if (newAgents[agentId]) {
          newAgents[agentId] = {
            ...newAgents[agentId],
            status: "running",
            task: event.data?.task || event.data?.message || newAgents[agentId].task,
            progress: event.data?.progress !== undefined 
              ? event.data.progress 
              : (event.data?.step !== undefined ? ((event.data.step + 1) / (event.data?.total_steps || 5)) * 100 : null),
          };
        }
      } else if (event.type === EVENT_TYPES.AGENT_COMPLETED || event.type === EVENT_TYPES.WORKFLOW_COMPLETED) {
        if (newAgents[agentId]) {
          newAgents[agentId] = {
            ...newAgents[agentId],
            status: "completed",
            task: "Completed",
            progress: 100,
          };
        }
      } else if (event.type === EVENT_TYPES.WORKFLOW_STEP_COMPLETED) {
        if (newAgents[agentId]) {
          newAgents[agentId] = {
            ...newAgents[agentId],
            task: event.data?.message || `Step ${event.data?.step} completed`,
            progress: event.data?.step !== undefined && event.data?.total_steps
              ? ((event.data.step + 1) / event.data.total_steps) * 100
              : newAgents[agentId].progress,
          };
        }
      } else if (event.type === EVENT_TYPES.AGENT_ERROR) {
        if (newAgents[agentId]) {
          newAgents[agentId] = {
            ...newAgents[agentId],
            status: "error",
            error: event.data?.error || "Unknown error",
          };
        }
      }
    });

    setAgents(newAgents);
  }, [events]);

  const filteredAgents = Object.values(agents).filter((agent) => {
    if (filter === "all") return true;
    if (filter === "running") return agent.status === "running";
    if (filter === "completed") return agent.status === "completed";
    if (filter === "error") return agent.status === "error";
    return true;
  });

  const statusCounts = {
    all: Object.keys(agents).length,
    running: Object.values(agents).filter((a) => a.status === "running").length,
    completed: Object.values(agents).filter((a) => a.status === "completed").length,
    error: Object.values(agents).filter((a) => a.status === "error").length,
  };

  const activeAgents = Object.values(agents).filter((a) => a.status === "running");
  const idleAgents = Object.values(agents).filter((a) => a.status === "idle" || !a.status);

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-white">AI Agent Panel</h3>
            <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`} />
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              <span className="text-slate-400">{statusCounts.running} Active</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-slate-400">{statusCounts.completed} Done</span>
            </div>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2">
          {[
            { key: "all", label: "All", count: statusCounts.all },
            { key: "running", label: "Active", count: statusCounts.running },
            { key: "completed", label: "Completed", count: statusCounts.completed },
            { key: "error", label: "Error", count: statusCounts.error },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setFilter(tab.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                filter === tab.key
                  ? "bg-blue-600 text-white"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              {tab.label}
              {tab.count > 0 && (
                <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-xs ${
                  filter === tab.key ? "bg-blue-500" : "bg-slate-600"
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Agent list */}
      <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
        {filteredAgents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <span className="text-4xl mb-2">🤖</span>
            <p>No agents active</p>
            <p className="text-xs mt-1">Agents will appear here when work starts</p>
          </div>
        ) : (
          filteredAgents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))
        )}
      </div>

      {/* Summary footer */}
      {activeAgents.length > 0 && (
        <div className="p-3 border-t border-slate-700 bg-slate-900/50">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span>{activeAgents.length} agent{activeAgents.length !== 1 ? "s" : ""} working...</span>
          </div>
        </div>
      )}
    </div>
  );
}
