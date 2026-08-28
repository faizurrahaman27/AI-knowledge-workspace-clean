import { useState, useEffect, useCallback, useRef } from "react";
import { API_BASE_URL, getWebsocketUrl } from "./axios";

export const EVENT_TYPES = {
  // Document events
  DOCUMENT_UPLOADED: "document:uploaded",
  DOCUMENT_PROCESSING: "document:processing",
  DOCUMENT_PROCESSED: "document:processed",
  DOCUMENT_INDEXED: "document:indexed",
  
  // Pipeline stages
  PIPELINE_START: "pipeline:start",
  OCR_STARTED: "ocr:started",
  OCR_COMPLETED: "ocr:completed",
  CLEANING_STARTED: "cleaning:started",
  CLEANING_COMPLETED: "cleaning:completed",
  CHUNKING_STARTED: "chunking:started",
  CHUNKING_COMPLETED: "chunking:completed",
  EMBEDDING_STARTED: "embedding:started",
  EMBEDDING_COMPLETED: "embedding:completed",
  ENTITY_EXTRACTION_STARTED: "entity:extraction:started",
  ENTITY_EXTRACTION_COMPLETED: "entity:extraction:completed",
  RELATIONSHIP_EXTRACTION_STARTED: "relationship:extraction:started",
  RELATIONSHIP_EXTRACTION_COMPLETED: "relationship:extraction:completed",
  KNOWLEDGE_GRAPH_STARTED: "knowledge:graph:started",
  KNOWLEDGE_GRAPH_COMPLETED: "knowledge:graph:completed",
  INDEXING_STARTED: "indexing:started",
  INDEXING_COMPLETED: "indexing:completed",
  
  // Agent events
  AGENT_STARTED: "agent:started",
  AGENT_PROGRESS: "agent:progress",
  AGENT_COMPLETED: "agent:completed",
  AGENT_ERROR: "agent:error",
  
  // RAG events
  RAG_QUERY_STARTED: "rag:query:started",
  RAG_RETRIEVAL_STARTED: "rag:retrieval:started",
  RAG_RETRIEVAL_COMPLETED: "rag:retrieval:completed",
  RAG_RERANKING_STARTED: "rag:reranking:started",
  RAG_RERANKING_COMPLETED: "rag:reranking:completed",
  RAG_GENERATION_STARTED: "rag:generation:started",
  RAG_STREAMING: "rag:streaming",
  RAG_COMPLETED: "rag:completed",
  
  // Workflow events
  WORKFLOW_STARTED: "workflow:started",
  WORKFLOW_STEP_STARTED: "workflow:step:started",
  WORKFLOW_STEP_COMPLETED: "workflow:step:completed",
  WORKFLOW_COMPLETED: "workflow:completed",
  WORKFLOW_FAILED: "workflow:failed",
  
  // Execution events
  EXECUTION_STARTED: "execution:started",
  EXECUTION_PROGRESS: "execution:progress",
  EXECUTION_COMPLETED: "execution:completed",
  EXECUTION_FAILED: "execution:failed",
  
  // Research events
  RESEARCH_STARTED: "research:started",
  RESEARCH_PLANNING: "research:planning",
  RESEARCH_SEARCHING: "research:searching",
  RESEARCH_VERIFYING: "research:verifying",
  RESEARCH_COMPLETED: "research:completed",
  
  // System events
  SYSTEM_STATUS: "system:status",
  SYSTEM_ERROR: "system:error",
};

export const PIPELINE_STAGES = [
  { key: "ocr", label: "OCR", icon: "📄", duration: null },
  { key: "cleaning", label: "Cleaning", icon: "🧹", duration: null },
  { key: "language_detection", label: "Language Detection", icon: "🌐", duration: null },
  { key: "layout_detection", label: "Layout Detection", icon: "📐", duration: null },
  { key: "chunking", label: "Chunking", icon: "✂️", duration: null },
  { key: "embedding", label: "Embedding", icon: "🔢", duration: null },
  { key: "entity_extraction", label: "Entity Extraction", icon: "🏷️", duration: null },
  { key: "relationship_extraction", label: "Relationships", icon: "🔗", duration: null },
  { key: "knowledge_graph", label: "Knowledge Graph", icon: "🕸️", duration: null },
  { key: "indexing", label: "Indexing", icon: "📚", duration: null },
];

export function useEventStream(workspaceId, options = {}) {
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  
  const {
    eventTypes = Object.values(EVENT_TYPES),
    maxEvents = 100,
    autoReconnect = true,
    onEvent = null,
  } = options;

  const connect = useCallback(() => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      // Connect to dedicated event stream endpoint
      const wsUrl = getWebsocketUrl(`/ws/events?token=${token}${workspaceId ? `&workspace_id=${workspaceId}` : ''}`);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        console.log("Event stream connected");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle different message types
          if (data.type === "connected") {
            console.log("Event stream authenticated:", data);
            return;
          }
          
          if (data.type === "heartbeat" || data.type === "pong") {
            return; // Skip heartbeats
          }
          
          // Filter by event types
          if (eventTypes.length === 0 || eventTypes.includes(data.type)) {
            const newEvent = {
              ...data,
              timestamp: data.timestamp || new Date().toISOString(),
              event_id: data.event_id || `${Date.now()}-${Math.random()}`,
            };
            
            setEvents((prev) => {
              const updated = [newEvent, ...prev];
              return updated.slice(0, maxEvents);
            });
            
            if (onEvent) {
              onEvent(newEvent);
            }
          }
        } catch (e) {
          console.error("Failed to parse event:", e);
        }
      };

      ws.onerror = (err) => {
        setError("WebSocket error");
        console.error("WebSocket error:", err);
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log("Event stream disconnected");
        
        if (autoReconnect) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log("Reconnecting to event stream...");
            connect();
          }, 3000);
        }
      };
    } catch (e) {
      setError("Failed to connect");
      console.error("Failed to connect:", e);
    }
  }, [workspaceId, eventTypes, maxEvents, autoReconnect, onEvent]);

  useEffect(() => {
    connect();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const sendEvent = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return {
    events,
    isConnected,
    error,
    sendEvent,
    reconnect: connect,
  };
}

export function useAgentStatus() {
  const [agents, setAgents] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const { events } = useEventStream(null, {
    autoReconnect: false,
    eventTypes: [
      EVENT_TYPES.AGENT_STARTED,
      EVENT_TYPES.AGENT_PROGRESS,
      EVENT_TYPES.AGENT_COMPLETED,
      EVENT_TYPES.AGENT_ERROR,
    ],
  });

  useEffect(() => {
    const agentEvents = events.filter(
      (e) =>
        e.type === EVENT_TYPES.AGENT_STARTED ||
        e.type === EVENT_TYPES.AGENT_PROGRESS ||
        e.type === EVENT_TYPES.AGENT_COMPLETED ||
        e.type === EVENT_TYPES.AGENT_ERROR
    );

    if (agentEvents.length > 0) {
      const newAgents = { ...agents };
      
      agentEvents.forEach((event) => {
        const agentId = event.agent_id || event.data?.agent_id;
        if (!agentId) return;

        if (event.type === EVENT_TYPES.AGENT_STARTED) {
          newAgents[agentId] = {
            id: agentId,
            name: event.data?.agent_name || agentId,
            status: "running",
            task: event.data?.task || "Initializing...",
            progress: 0,
            startedAt: event.timestamp,
            elapsed: 0,
          };
        } else if (event.type === EVENT_TYPES.AGENT_PROGRESS) {
          if (newAgents[agentId]) {
            newAgents[agentId] = {
              ...newAgents[agentId],
              status: "running",
              task: event.data?.task || newAgents[agentId].task,
              progress: event.data?.progress || newAgents[agentId].progress,
              elapsed: Date.now() - new Date(newAgents[agentId].startedAt).getTime(),
            };
          }
        } else if (event.type === EVENT_TYPES.AGENT_COMPLETED) {
          if (newAgents[agentId]) {
            newAgents[agentId] = {
              ...newAgents[agentId],
              status: "completed",
              task: event.data?.task || "Completed",
              progress: 100,
              elapsed: Date.now() - new Date(newAgents[agentId].startedAt).getTime(),
            };
          }
        } else if (event.type === EVENT_TYPES.AGENT_ERROR) {
          if (newAgents[agentId]) {
            newAgents[agentId] = {
              ...newAgents[agentId],
              status: "error",
              task: event.data?.error || "Error",
              error: true,
            };
          }
        }
      });

      setAgents(newAgents);
      setIsConnected(true);
    }
  }, [events]);

  return { agents, isConnected };
}

export function usePipelineStatus() {
  const [stages, setStages] = useState(
    PIPELINE_STAGES.map((s) => ({ ...s, status: "pending", startTime: null, endTime: null }))
  );
  const [currentStage, setCurrentStage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [documentId, setDocumentId] = useState(null);
  
  const { events } = useEventStream(null, {
    autoReconnect: false,
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
    ],
  });

  useEffect(() => {
    const pipelineEvents = events.filter(
      (e) =>
        e.type.includes(":started") ||
        e.type.includes(":completed") ||
        e.type === EVENT_TYPES.PIPELINE_START ||
        e.type === EVENT_TYPES.DOCUMENT_PROCESSED
    );

    if (pipelineEvents.length > 0) {
      const latestEvent = pipelineEvents[0];
      
      // Update document ID
      if (latestEvent.document_id) {
        setDocumentId(latestEvent.document_id);
      }

      setStages((prev) => {
        const updated = [...prev];
        
        // Find which stage this event belongs to
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
              };
              // Calculate duration
              if (updated[stageIndex].startTime) {
                const duration =
                  new Date(latestEvent.timestamp) - new Date(updated[stageIndex].startTime);
                updated[stageIndex] = {
                  ...updated[stageIndex],
                  duration,
                };
              }
            }
          }
        }

        // Check if pipeline is complete
        if (latestEvent.type === EVENT_TYPES.DOCUMENT_PROCESSED) {
          setIsProcessing(false);
          setCurrentStage(null);
        }

        return updated;
      });
    }
  }, [events]);

  const reset = useCallback(() => {
    setStages(
      PIPELINE_STAGES.map((s) => ({ ...s, status: "pending", startTime: null, endTime: null, duration: null }))
    );
    setCurrentStage(null);
    setIsProcessing(false);
    setDocumentId(null);
  }, []);

  return {
    stages,
    currentStage,
    isProcessing,
    documentId,
    reset,
    progress: stages.filter((s) => s.status === "completed").length / stages.length,
  };
}

export default {
  useEventStream,
  useAgentStatus,
  usePipelineStatus,
  EVENT_TYPES,
  PIPELINE_STAGES,
};
