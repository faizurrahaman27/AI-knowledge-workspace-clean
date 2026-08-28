import { useState, useEffect } from "react";
import { useEventStream, EVENT_TYPES } from "../api/events";
import { executeWorkflow, getTemplates, getExecutionStatus } from "../api/execution";
import api from "../api/axios";

export default function ExecutionMonitor() {
  const [executions, setExecutions] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [status, setStatus] = useState(null);
  const [selectedExecution, setSelectedExecution] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const { events, isConnected } = useEventStream(1, {
    maxEvents: 100,
    eventTypes: [
      EVENT_TYPES.EXECUTION_STARTED,
      EVENT_TYPES.EXECUTION_PROGRESS,
      EVENT_TYPES.EXECUTION_COMPLETED,
      EVENT_TYPES.EXECUTION_FAILED,
      EVENT_TYPES.WORKFLOW_STARTED,
      EVENT_TYPES.WORKFLOW_STEP_STARTED,
      EVENT_TYPES.WORKFLOW_STEP_COMPLETED,
      EVENT_TYPES.WORKFLOW_COMPLETED,
      EVENT_TYPES.WORKFLOW_FAILED,
    ],
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    // Update executions from events
    if (events.length === 0) return;

    const newExecutions = [...executions];
    
    events.forEach((event) => {
      const execId = event.data?.execution_id || event.workflow_id;
      if (!execId) return;

      const existingIndex = newExecutions.findIndex((e) => e.id === execId);

      if (
        event.type === EVENT_TYPES.EXECUTION_STARTED ||
        event.type === EVENT_TYPES.WORKFLOW_STARTED
      ) {
        const newExec = {
          id: execId,
          type: event.type.includes("execution") ? "execution" : "workflow",
          name: event.data?.name || event.data?.workflow_name || execId,
          status: "running",
          progress: 0,
          startedAt: event.timestamp,
          steps: event.data?.steps || [],
          logs: [`[${new Date(event.timestamp).toLocaleTimeString()}] Started`],
        };

        if (existingIndex >= 0) {
          newExecutions[existingIndex] = newExec;
        } else {
          newExecutions.unshift(newExec);
        }
      } else if (
        event.type === EVENT_TYPES.EXECUTION_PROGRESS ||
        event.type === EVENT_TYPES.WORKFLOW_STEP_STARTED
      ) {
        if (existingIndex >= 0) {
          newExecutions[existingIndex] = {
            ...newExecutions[existingIndex],
            progress: event.data?.progress || newExecutions[existingIndex].progress,
            currentStep: event.data?.step_name || event.data?.message,
            logs: [
              ...newExecutions[existingIndex].logs,
              `[${new Date(event.timestamp).toLocaleTimeString()}] ${event.data?.message || "Processing..."}`,
            ],
          };
        }
      } else if (
        event.type === EVENT_TYPES.EXECUTION_COMPLETED ||
        event.type === EVENT_TYPES.WORKFLOW_COMPLETED
      ) {
        if (existingIndex >= 0) {
          newExecutions[existingIndex] = {
            ...newExecutions[existingIndex],
            status: "completed",
            progress: 100,
            completedAt: event.timestamp,
            outputs: event.data?.outputs || [],
            logs: [
              ...newExecutions[existingIndex].logs,
              `[${new Date(event.timestamp).toLocaleTimeString()}] Completed successfully`,
            ],
          };
        }
      } else if (
        event.type === EVENT_TYPES.EXECUTION_FAILED ||
        event.type === EVENT_TYPES.WORKFLOW_FAILED
      ) {
        if (existingIndex >= 0) {
          newExecutions[existingIndex] = {
            ...newExecutions[existingIndex],
            status: "failed",
            error: event.data?.error || "Unknown error",
            logs: [
              ...newExecutions[existingIndex].logs,
              `[${new Date(event.timestamp).toLocaleTimeString()}] Error: ${event.data?.error || "Unknown"}`,
            ],
          };
        }
      }
    });

    setExecutions(newExecutions);
  }, [events]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [templatesRes, statusRes, historyRes] = await Promise.allSettled([
        getTemplates(),
        getExecutionStatus(),
        api.get("/execution/history", { params: { limit: 20 } }),
      ]);

      if (templatesRes.status === "fulfilled") {
        setTemplates(templatesRes.value.data.templates || []);
      }
      if (statusRes.status === "fulfilled") {
        setStatus(statusRes.value.data);
      }
      if (historyRes.status === "fulfilled") {
        setExecutions(historyRes.value.data.executions || []);
      }
    } catch (err) {
      console.error("Failed to fetch execution data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async (executionId, filename) => {
    try {
      const response = await api.get(`/execution/${executionId}/outputs/${filename}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Download failed:", err);
    }
  };

  const filteredExecutions = executions.filter((exec) => {
    if (filter === "all") return true;
    if (filter === "running") return exec.status === "running";
    if (filter === "completed") return exec.status === "completed";
    if (filter === "failed") return exec.status === "failed";
    return true;
  });

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-white">Execution Monitor</h3>
            <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`} />
          </div>
          <button
            onClick={fetchData}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-700 text-slate-300 hover:bg-slate-600 transition"
          >
            🔄 Refresh
          </button>
        </div>

        {/* Status summary */}
        {status && (
          <div className="grid grid-cols-4 gap-2 mb-3">
            <div className="bg-slate-700/50 rounded-lg p-2 text-center">
              <p className="text-lg font-bold text-white">{status.total || 0}</p>
              <p className="text-xs text-slate-400">Total</p>
            </div>
            <div className="bg-blue-900/30 rounded-lg p-2 text-center">
              <p className="text-lg font-bold text-blue-400">{status.active || 0}</p>
              <p className="text-xs text-slate-400">Active</p>
            </div>
            <div className="bg-green-900/30 rounded-lg p-2 text-center">
              <p className="text-lg font-bold text-green-400">{status.completed_today || 0}</p>
              <p className="text-xs text-slate-400">Completed</p>
            </div>
            <div className="bg-red-900/30 rounded-lg p-2 text-center">
              <p className="text-lg font-bold text-red-400">{status.failed_today || 0}</p>
              <p className="text-xs text-slate-400">Failed</p>
            </div>
          </div>
        )}

        {/* Filter tabs */}
        <div className="flex gap-2">
          {[
            { key: "all", label: "All", count: executions.length },
            { key: "running", label: "Running", count: executions.filter((e) => e.status === "running").length },
            { key: "completed", label: "Completed", count: executions.filter((e) => e.status === "completed").length },
            { key: "failed", label: "Failed", count: executions.filter((e) => e.status === "failed").length },
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

      {/* Execution list */}
      <div className="max-h-96 overflow-y-auto">
        {filteredExecutions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <span className="text-4xl mb-2">⚡</span>
            <p>No executions yet</p>
            <p className="text-xs mt-1">Execute a workflow to see it here</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700">
            {filteredExecutions.map((execution) => (
              <ExecutionItem
                key={execution.id}
                execution={execution}
                isSelected={selectedExecution?.id === execution.id}
                onClick={() => setSelectedExecution(selectedExecution?.id === execution.id ? null : execution)}
                onDownload={handleDownload}
              />
            ))}
          </div>
        )}
      </div>

      {/* Detail panel */}
      {selectedExecution && (
        <ExecutionDetail execution={selectedExecution} onDownload={handleDownload} />
      )}
    </div>
  );
}

function ExecutionItem({ execution, isSelected, onClick, onDownload }) {
  const getStatusColor = (status) => {
    switch (status) {
      case "completed":
        return "bg-green-500/20 text-green-400";
      case "failed":
        return "bg-red-500/20 text-red-400";
      case "running":
        return "bg-blue-500/20 text-blue-400";
      default:
        return "bg-slate-500/20 text-slate-400";
    }
  };

  const elapsed = execution.startedAt
    ? Math.floor((Date.now() - new Date(execution.startedAt).getTime()) / 1000)
    : 0;

  const elapsedStr = elapsed > 60
    ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
    : `${elapsed}s`;

  return (
    <div
      onClick={onClick}
      className={`p-4 cursor-pointer transition ${
        isSelected ? "bg-blue-900/20" : "hover:bg-slate-700/50"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`w-3 h-3 rounded-full ${
            execution.status === "running" ? "bg-blue-500 animate-pulse" :
            execution.status === "completed" ? "bg-green-500" :
            execution.status === "failed" ? "bg-red-500" : "bg-slate-500"
          }`} />
          <div>
            <p className="font-medium text-white">{execution.name || execution.id}</p>
            <p className="text-xs text-slate-400">
              {execution.type} • {elapsedStr}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(execution.status)}`}>
            {execution.status}
          </span>
          {execution.progress !== undefined && (
            <span className="text-xs text-slate-400">{Math.round(execution.progress)}%</span>
          )}
        </div>
      </div>

      {execution.status === "running" && execution.progress !== undefined && (
        <div className="mt-2 w-full bg-slate-700 rounded-full h-1">
          <div
            className="bg-blue-500 h-1 rounded-full transition-all"
            style={{ width: `${execution.progress}%` }}
          />
        </div>
      )}

      {execution.currentStep && (
        <p className="text-xs text-slate-400 mt-1">
          Current: {execution.currentStep}
        </p>
      )}
    </div>
  );
}

function ExecutionDetail({ execution, onDownload }) {
  return (
    <div className="p-4 border-t border-slate-700 bg-slate-900/50">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="font-medium text-white">Execution Details</h4>
          <p className="text-xs text-slate-400">{execution.id}</p>
        </div>
        {execution.error && (
          <span className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded text-xs">
            Error
          </span>
        )}
      </div>

      {/* Steps */}
      {execution.steps && execution.steps.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-slate-400 mb-2">Steps</p>
          <div className="space-y-1">
            {execution.steps.map((step, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className={`w-4 h-4 rounded-full flex items-center justify-center text-xs ${
                  step.status === "completed" ? "bg-green-500 text-white" :
                  step.status === "running" ? "bg-blue-500 text-white animate-pulse" :
                  "bg-slate-600 text-slate-300"
                }`}>
                  {step.status === "completed" ? "✓" : i + 1}
                </span>
                <span className="text-slate-300">{step.name || step}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Outputs */}
      {execution.outputs && execution.outputs.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-slate-400 mb-2">Outputs</p>
          <div className="space-y-1">
            {execution.outputs.map((output, i) => (
              <div key={i} className="flex items-center justify-between bg-slate-700/50 rounded p-2">
                <span className="text-sm text-slate-300">{output.filename}</span>
                <button
                  onClick={() => onDownload(execution.id, output.filename)}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  Download
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Logs */}
      {execution.logs && execution.logs.length > 0 && (
        <div>
          <p className="text-xs text-slate-400 mb-2">Logs</p>
          <div className="bg-slate-800 rounded p-2 max-h-32 overflow-y-auto">
            {execution.logs.map((log, i) => (
              <p key={i} className="text-xs text-slate-400 font-mono">{log}</p>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {execution.error && (
        <div className="mt-3 p-3 bg-red-900/30 border border-red-800 rounded-lg">
          <p className="text-xs text-red-400">{execution.error}</p>
        </div>
      )}
    </div>
  );
}
