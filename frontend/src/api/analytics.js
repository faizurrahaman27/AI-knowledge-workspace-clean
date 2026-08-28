import api from "./axios";

// ============================================================================
// Analytics API
// ============================================================================

// Get system overview stats
export const getOverviewStats = () => api.get("/analytics/overview");

// Get learning analytics
export const getLearningAnalytics = () => api.get("/analytics/learning");

// Get document analytics
export const getDocumentAnalytics = () => api.get("/analytics/documents");

// Get user engagement metrics
export const getEngagementMetrics = () => api.get("/analytics/engagement");

// Get study progress
export const getStudyProgress = () => api.get("/analytics/study-progress");

// Get knowledge graph stats
export const getKnowledgeGraphStats = () => api.get("/analytics/knowledge-graph");

// Get multi-agent stats
export const getMultiAgentStats = () => api.get("/analytics/multi-agent");

// Get autonomous learning stats
export const getAutonomousStats = () => api.get("/analytics/autonomous");

// Get workflow execution stats
export const getWorkflowStats = () => api.get("/analytics/workflows");

// Get real-time metrics
export const getRealTimeMetrics = () => api.get("/metrics/realtime");

// Get historical metrics
export const getHistoricalMetrics = (startDate, endDate) => 
  api.get("/metrics/historical", { params: { start_date: startDate, end_date: endDate } });

export default {
  getOverviewStats,
  getLearningAnalytics,
  getDocumentAnalytics,
  getEngagementMetrics,
  getStudyProgress,
  getKnowledgeGraphStats,
  getMultiAgentStats,
  getAutonomousStats,
  getWorkflowStats,
  getRealTimeMetrics,
  getHistoricalMetrics,
};
