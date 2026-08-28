import { useState } from "react";
import ActivityCenter from "./ActivityCenter";
import AgentPanel from "./AgentPanel";
import PipelineVisualizer from "./PipelineVisualizer";
import TaskTimeline from "./TaskTimeline";
import KnowledgeGraph from "./KnowledgeGraph";
import ExecutionMonitor from "./ExecutionMonitor";
import ChunkVisualizer from "./ChunkVisualizer";

export default function LiveActivity({ workspaceId, documentId }) {
  const [activeTab, setActiveTab] = useState("activity");

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      {/* Tab navigation */}
      <div className="flex border-b border-slate-700 overflow-x-auto">
        {[
          { key: "activity", label: "Activity", icon: "📡" },
          { key: "agents", label: "Agents", icon: "🤖" },
          { key: "pipeline", label: "Pipeline", icon: "⚙️" },
          { key: "timeline", label: "Timeline", icon: "📋" },
          { key: "execution", label: "Jobs", icon: "⚡" },
          { key: "graph", label: "Graph", icon: "🕸️" },
          { key: "chunks", label: "Chunks", icon: "📄" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition border-b-2 ${
              activeTab === tab.key
                ? "text-white border-blue-500 bg-slate-700/50"
                : "text-slate-400 border-transparent hover:text-white hover:bg-slate-700/30"
            }`}
          >
            <span>{tab.icon}</span>
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4">
        {activeTab === "activity" && <ActivityCenter workspaceId={workspaceId} />}
        {activeTab === "agents" && <AgentPanel workspaceId={workspaceId} />}
        {activeTab === "pipeline" && <PipelineVisualizer workspaceId={workspaceId} documentId={documentId} />}
        {activeTab === "timeline" && <TaskTimeline workspaceId={workspaceId} />}
        {activeTab === "execution" && <ExecutionMonitor />}
        {activeTab === "graph" && <KnowledgeGraph documentId={documentId} workspaceId={workspaceId} />}
        {activeTab === "chunks" && (
          <ChunkVisualizer 
            chunks={[]} 
            isLoading={false} 
          />
        )}
      </div>
    </div>
  );
}
