import { useEffect, useState } from "react";
import { useEventStream, EVENT_TYPES, PIPELINE_STAGES } from "../api/events";

function PipelineStage({ stage, index, totalStages }) {
  const getStatusColor = (status) => {
    switch (status) {
      case "completed":
        return "bg-green-500 border-green-400 text-white";
      case "running":
        return "bg-blue-500 border-blue-400 text-white animate-pulse";
      case "error":
        return "bg-red-500 border-red-400 text-white";
      default:
        return "bg-slate-700 border-slate-600 text-slate-400";
    }
  };

  const getConnectorColor = (status) => {
    return status === "completed" ? "bg-green-500" : "bg-slate-600";
  };

  return (
    <div className="flex flex-col items-center">
      <div
        className={`w-16 h-16 rounded-xl border-2 flex items-center justify-center transition-all duration-300 ${getStatusColor(
          stage.status
        )}`}
      >
        <span className="text-2xl">{stage.icon}</span>
      </div>
      <div className="mt-2 text-center">
        <p className="text-sm font-medium text-white">{stage.label}</p>
        {stage.duration && (
          <p className="text-xs text-slate-400">
            {stage.duration < 1000
              ? `${stage.duration}ms`
              : `${(stage.duration / 1000).toFixed(1)}s`}
          </p>
        )}
        {stage.status === "running" && (
          <div className="mt-1 w-full bg-slate-700 rounded-full h-1">
            <div className="bg-blue-500 h-1 rounded-full animate-pulse w-3/4" />
          </div>
        )}
      </div>

      {/* Connector line */}
      {index < totalStages - 1 && (
        <div className={`w-0.5 h-8 transition-colors ${getConnectorColor(stage.status)}`} />
      )}
    </div>
  );
}

function WorkflowStep({ step, isActive, isCompleted }) {
  return (
    <div
      className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
        isActive
          ? "bg-blue-900/30 border border-blue-500"
          : isCompleted
          ? "bg-green-900/20 border border-green-800"
          : "bg-slate-800/50 border border-slate-700"
      }`}
    >
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
          isCompleted
            ? "bg-green-500 text-white"
            : isActive
            ? "bg-blue-500 text-white animate-pulse"
            : "bg-slate-700 text-slate-400"
        }`}
      >
        {isCompleted ? "✓" : step.step_number}
      </div>
      <div className="flex-1">
        <p className={`font-medium ${isActive ? "text-white" : isCompleted ? "text-green-400" : "text-slate-400"}`}>
          {step.name}
        </p>
        {step.description && (
          <p className="text-xs text-slate-500">{step.description}</p>
        )}
      </div>
      {step.progress !== undefined && (
        <div className="text-xs text-slate-400">{Math.round(step.progress)}%</div>
      )}
    </div>
  );
}

export default function PipelineVisualizer({ workspaceId, documentId }) {
  const [stages, setStages] = useState(
    PIPELINE_STAGES.map((s) => ({ ...s, status: "pending", startTime: null, endTime: null, duration: null }))
  );
  const [currentStage, setCurrentStage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentDocId, setCurrentDocId] = useState(documentId);
  const [workflowSteps, setWorkflowSteps] = useState([]);
  const [workflowProgress, setWorkflowProgress] = useState(0);
  
  const { events, isConnected } = useEventStream(workspaceId || 1, {
    maxEvents: 100,
    eventTypes: [
      EVENT_TYPES.PIPELINE_START,
      EVENT_TYPES.OCR_STARTED,
      EVENT_TYPES.OCR_COMPLETED,
      EVENT_TYPES.CLEANING_STARTED,
      EVENT_TYPES.CLEANING_COMPLETED,
      EVENT_TYPES.CHUNKING_STARTED,
      EVENT_TYPES.CHUNKING_COMPLETED,
      EVENT_TYPES.EMBEDDING_STARTED,
      EVENT_TYPES.EMBEDDING_COMPLETED,
      EVENT_TYPES.ENTITY_EXTRACTION_STARTED,
      EVENT_TYPES.ENTITY_EXTRACTION_COMPLETED,
      EVENT_TYPES.RELATIONSHIP_EXTRACTION_STARTED,
      EVENT_TYPES.RELATIONSHIP_EXTRACTION_COMPLETED,
      EVENT_TYPES.KNOWLEDGE_GRAPH_STARTED,
      EVENT_TYPES.KNOWLEDGE_GRAPH_COMPLETED,
      EVENT_TYPES.INDEXING_STARTED,
      EVENT_TYPES.INDEXING_COMPLETED,
      EVENT_TYPES.DOCUMENT_PROCESSED,
      EVENT_TYPES.WORKFLOW_STARTED,
      EVENT_TYPES.WORKFLOW_STEP_STARTED,
      EVENT_TYPES.WORKFLOW_STEP_COMPLETED,
      EVENT_TYPES.WORKFLOW_COMPLETED,
      EVENT_TYPES.EXECUTION_STARTED,
      EVENT_TYPES.EXECUTION_PROGRESS,
      EVENT_TYPES.EXECUTION_COMPLETED,
    ],
  });

  const stageMap = {
    [EVENT_TYPES.OCR_STARTED]: "ocr",
    [EVENT_TYPES.OCR_COMPLETED]: "ocr",
    [EVENT_TYPES.CLEANING_STARTED]: "cleaning",
    [EVENT_TYPES.CLEANING_COMPLETED]: "cleaning",
    [EVENT_TYPES.CHUNKING_STARTED]: "chunking",
    [EVENT_TYPES.CHUNKING_COMPLETED]: "chunking",
    [EVENT_TYPES.EMBEDDING_STARTED]: "embedding",
    [EVENT_TYPES.EMBEDDING_COMPLETED]: "embedding",
    [EVENT_TYPES.ENTITY_EXTRACTION_STARTED]: "entity_extraction",
    [EVENT_TYPES.ENTITY_EXTRACTION_COMPLETED]: "entity_extraction",
    [EVENT_TYPES.RELATIONSHIP_EXTRACTION_STARTED]: "relationship_extraction",
    [EVENT_TYPES.RELATIONSHIP_EXTRACTION_COMPLETED]: "relationship_extraction",
    [EVENT_TYPES.KNOWLEDGE_GRAPH_STARTED]: "knowledge_graph",
    [EVENT_TYPES.KNOWLEDGE_GRAPH_COMPLETED]: "knowledge_graph",
    [EVENT_TYPES.INDEXING_STARTED]: "indexing",
    [EVENT_TYPES.INDEXING_COMPLETED]: "indexing",
  };

  useEffect(() => {
    if (events.length === 0) return;

    const latestEvent = events[0];
    
    // Track document ID
    if (latestEvent.document_id) {
      setCurrentDocId(latestEvent.document_id);
    }

    // Handle workflow events
    if (
      latestEvent.type === EVENT_TYPES.WORKFLOW_STARTED ||
      latestEvent.type === EVENT_TYPES.EXECUTION_STARTED
    ) {
      setWorkflowSteps(
        (latestEvent.data?.steps || []).map((s, i) => ({
          ...s,
          step_number: i + 1,
          status: "pending",
        }))
      );
      setIsProcessing(true);
    }

    if (
      latestEvent.type === EVENT_TYPES.WORKFLOW_STEP_STARTED ||
      latestEvent.type === EVENT_TYPES.EXECUTION_PROGRESS
    ) {
      const stepIndex = latestEvent.data?.step;
      setWorkflowSteps((prev) => {
        const updated = [...prev];
        if (stepIndex !== undefined && updated[stepIndex]) {
          updated[stepIndex] = {
            ...updated[stepIndex],
            status: "running",
            progress: latestEvent.data?.progress,
          };
        }
        return updated;
      });
    }

    if (
      latestEvent.type === EVENT_TYPES.WORKFLOW_STEP_COMPLETED ||
      latestEvent.type === EVENT_TYPES.EXECUTION_PROGRESS
    ) {
      const stepIndex = latestEvent.data?.step;
      setWorkflowSteps((prev) => {
        const updated = [...prev];
        if (stepIndex !== undefined && updated[stepIndex]) {
          updated[stepIndex] = {
            ...updated[stepIndex],
            status: "completed",
            progress: 100,
          };
        }
        return updated;
      });

      // Update overall progress
      const completedSteps = latestEvent.data?.step + 1;
      const totalSteps = latestEvent.data?.total_steps || workflowSteps.length || 1;
      setWorkflowProgress((completedSteps / totalSteps) * 100);
    }

    if (
      latestEvent.type === EVENT_TYPES.WORKFLOW_COMPLETED ||
      latestEvent.type === EVENT_TYPES.EXECUTION_COMPLETED ||
      latestEvent.type === EVENT_TYPES.DOCUMENT_PROCESSED
    ) {
      setWorkflowSteps((prev) =>
        prev.map((s) => ({ ...s, status: "completed", progress: 100 }))
      );
      setWorkflowProgress(100);
      setIsProcessing(false);
      setCurrentStage(null);
    }

    // Handle pipeline events
    setStages((prev) => {
      const updated = [...prev];
      const stageKey = stageMap[latestEvent.type];

      if (stageKey) {
        const stageIndex = updated.findIndex((s) => s.key === stageKey);
        if (stageIndex !== -1) {
          if (latestEvent.type.includes(":started")) {
            updated[stageIndex] = {
              ...updated[stageIndex],
              status: "running",
              startTime: latestEvent.timestamp,
            };
            setCurrentStage(stageKey);
            setIsProcessing(true);
          } else if (latestEvent.type.includes(":completed")) {
            updated[stageIndex] = {
              ...updated[stageIndex],
              status: "completed",
              endTime: latestEvent.timestamp,
              duration: latestEvent.timestamp
                ? new Date(latestEvent.timestamp) - new Date(updated[stageIndex].startTime || latestEvent.timestamp)
                : null,
            };
          }
        }
      }

      return updated;
    });
  }, [events]);

  const completedCount = stages.filter((s) => s.status === "completed").length;
  const overallProgress = (completedCount / stages.length) * 100;

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-white">Pipeline Visualization</h3>
            {currentDocId && (
              <span className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-400">
                Doc: {currentDocId}
              </span>
            )}
          </div>
          <span className={`px-2 py-0.5 rounded text-xs ${
            isProcessing ? "bg-blue-500/20 text-blue-400 animate-pulse" : "bg-green-500/20 text-green-400"
          }`}>
            {isProcessing ? "Processing" : "Idle"}
          </span>
        </div>

        {/* Overall progress */}
        <div className="mb-2">
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>Overall Progress</span>
            <span>{Math.round(overallProgress)}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                isProcessing ? "bg-blue-500 animate-pulse" : "bg-green-500"
              }`}
              style={{ width: `${overallProgress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Pipeline stages */}
      <div className="p-6">
        <div className="flex flex-wrap justify-center gap-4">
          {stages.map((stage, index) => (
            <PipelineStage
              key={stage.key}
              stage={stage}
              index={index}
              totalStages={stages.length}
            />
          ))}
        </div>
      </div>

      {/* Workflow steps (if any) */}
      {workflowSteps.length > 0 && (
        <div className="p-4 border-t border-slate-700">
          <h4 className="text-sm font-medium text-white mb-3">Workflow Steps</h4>
          <div className="space-y-2">
            {workflowSteps.map((step, index) => (
              <WorkflowStep
                key={index}
                step={step}
                isActive={step.status === "running"}
                isCompleted={step.status === "completed"}
              />
            ))}
          </div>
        </div>
      )}

      {/* Execution progress (if workflow progress exists) */}
      {workflowProgress > 0 && (
        <div className="p-4 border-t border-slate-700">
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>Workflow Progress</span>
            <span>{Math.round(workflowProgress)}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-1">
            <div
              className="bg-purple-500 h-1 rounded-full transition-all duration-300 animate-pulse"
              style={{ width: `${workflowProgress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
