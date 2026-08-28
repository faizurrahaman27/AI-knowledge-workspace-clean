import { useState, useEffect } from "react";
import api from "../api/axios";

export default function BackgroundTasks() {
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchTasks();
    // Poll for updates
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await api.get("/tasks/");
      setTasks(response.data.tasks || []);
    } catch (err) {
      // Use demo tasks if API fails
      setTasks(DEMO_TASKS);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = async (taskId) => {
    try {
      await api.post(`/tasks/${taskId}/retry`);
      fetchTasks();
    } catch (err) {
      console.error("Retry failed:", err);
    }
  };

  const handleCancel = async (taskId) => {
    try {
      await api.post(`/tasks/${taskId}/cancel`);
      fetchTasks();
    } catch (err) {
      console.error("Cancel failed:", err);
    }
  };

  const pendingTasks = tasks.filter((t) => t.status === "pending" || t.status === "running");
  const completedTasks = tasks.filter((t) => t.status === "completed");
  const failedTasks = tasks.filter((t) => t.status === "failed");

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-slate-700 rounded w-1/4"></div>
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white">Background Tasks</h3>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
              {pendingTasks.length} Running
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              {completedTasks.length} Done
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              {failedTasks.length} Failed
            </span>
          </div>
        </div>
      </div>

      {/* Tasks list */}
      <div className="max-h-96 overflow-y-auto">
        {tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <span className="text-4xl mb-2">📋</span>
            <p>No background tasks</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700">
            {tasks.map((task) => (
              <TaskItem
                key={task.id}
                task={task}
                onRetry={handleRetry}
                onCancel={handleCancel}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TaskItem({ task, onRetry, onCancel }) {
  const getStatusStyles = (status) => {
    switch (status) {
      case "completed":
        return "border-l-green-500";
      case "failed":
        return "border-l-red-500";
      case "running":
        return "border-l-blue-500";
      case "pending":
        return "border-l-amber-500";
      default:
        return "border-l-slate-500";
    }
  };

  const elapsed = task.started_at
    ? Math.floor((Date.now() - new Date(task.started_at).getTime()) / 1000)
    : 0;

  const elapsedStr = elapsed > 60
    ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
    : `${elapsed}s`;

  return (
    <div className={`p-4 border-l-4 ${getStatusStyles(task.status)}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-white">{task.name || task.id}</h4>
            <span className={`px-2 py-0.5 rounded text-xs ${
              task.status === "completed" ? "bg-green-500/20 text-green-400" :
              task.status === "failed" ? "bg-red-500/20 text-red-400" :
              task.status === "running" ? "bg-blue-500/20 text-blue-400" :
              "bg-amber-500/20 text-amber-400"
            }`}>
              {task.status}
            </span>
          </div>

          {task.description && (
            <p className="text-sm text-slate-400 mt-1">{task.description}</p>
          )}

          <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
            {task.started_at && (
              <span>Started: {new Date(task.started_at).toLocaleTimeString()}</span>
            )}
            {task.status === "running" && (
              <span>Elapsed: {elapsedStr}</span>
            )}
            {task.completed_at && (
              <span>Duration: {Math.round((new Date(task.completed_at) - new Date(task.started_at)) / 1000)}s</span>
            )}
          </div>

          {/* Progress bar for running tasks */}
          {task.status === "running" && task.progress !== undefined && (
            <div className="mt-2">
              <div className="w-full bg-slate-700 rounded-full h-1.5">
                <div
                  className="bg-blue-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${task.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Error message */}
          {task.status === "failed" && task.error && (
            <p className="text-xs text-red-400 mt-2">Error: {task.error}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 ml-4">
          {task.status === "failed" && (
            <button
              onClick={() => onRetry(task.id)}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-xs font-medium text-white transition"
            >
              Retry
            </button>
          )}
          {(task.status === "running" || task.status === "pending") && (
            <button
              onClick={() => onCancel(task.id)}
              className="px-3 py-1.5 bg-slate-700 hover:bg-red-600 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Demo tasks for display
const DEMO_TASKS = [
  {
    id: "task-1",
    name: "Document Processing",
    description: "Processing research_paper.pdf",
    status: "running",
    progress: 65,
    started_at: new Date(Date.now() - 30000).toISOString(),
  },
  {
    id: "task-2",
    name: "Knowledge Extraction",
    description: "Extracting entities from document",
    status: "pending",
    started_at: null,
  },
  {
    id: "task-3",
    name: "Embeddings Generation",
    description: "Generating vector embeddings",
    status: "completed",
    started_at: new Date(Date.now() - 120000).toISOString(),
    completed_at: new Date(Date.now() - 60000).toISOString(),
  },
  {
    id: "task-4",
    name: "Graph Update",
    description: "Updating knowledge graph",
    status: "failed",
    error: "Connection timeout",
    started_at: new Date(Date.now() - 180000).toISOString(),
  },
];
