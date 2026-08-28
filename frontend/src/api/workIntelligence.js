import api from "./axios";

// ============================================================================
// Work Intelligence API (Phase 9)
// ============================================================================

// Unified work intelligence analysis
export const analyzeWorkIntelligence = (data) => api.post("/work-intelligence/", data);

// Quick document analysis
export const quickAnalyze = (documentId) => api.post("/work-intelligence/quick-analyze", null, {
  params: { document_id: documentId }
});

// Intent analysis
export const analyzeIntent = (data) => api.post("/work-intelligence/intent/analyze", data);

// Document classification
export const classifyDocument = (data) => api.post("/work-intelligence/classify", data);

// Get document types
export const getDocumentTypes = () => api.get("/work-intelligence/document-types");

// Get all actions
export const getAllActions = (params = {}) => api.get("/work-intelligence/actions", { params });

// Get action by ID
export const getAction = (actionId) => api.get(`/work-intelligence/actions/${actionId}`);

// Execute action
export const executeAction = (data) => api.post("/work-intelligence/actions/execute", data);

// Get actions summary
export const getActionsSummary = () => api.get("/work-intelligence/actions/summary");

// Get recommendations
export const getRecommendations = (data) => api.post("/work-intelligence/recommendations", data);

// Generate questions
export const generateQuestions = (data) => api.post("/work-intelligence/questions/generate", data);

// Get available workflows
export const getWorkIntelligenceWorkflows = () => api.get("/work-intelligence/workflows");

// Get workflow for action
export const getWorkflowForAction = (actionId) => api.get(`/work-intelligence/workflows/from-action/${actionId}`);

// Get document context
export const getDocumentContext = (documentId) => api.get(`/work-intelligence/context/from-document/${documentId}`);

export default {
  analyzeWorkIntelligence,
  quickAnalyze,
  analyzeIntent,
  classifyDocument,
  getDocumentTypes,
  getAllActions,
  getAction,
  executeAction,
  getActionsSummary,
  getRecommendations,
  generateQuestions,
  getWorkIntelligenceWorkflows,
  getWorkflowForAction,
  getDocumentContext,
};
