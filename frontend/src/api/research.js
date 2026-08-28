import api from "./axios";

// ============================================================================
// Research OS API
// ============================================================================

// Get available research agents
export const getResearchAgents = () => api.get("/research/agents");

// Create research report
export const createResearchReport = (data) => api.post("/research/report", data);

// Get conflict analysis
export const analyzeConflicts = (sourceIds) => api.post("/research/conflicts", { source_ids: sourceIds });

// Generate evidence
export const generateEvidence = (claim, context) => api.post("/research/evidence", { claim, context });

// Get synthesis report
export const getSynthesis = (reportId) => api.get(`/research/synthesis/${reportId}`);

// List research reports
export const listReports = () => api.get("/research/reports");

// Get research plan
export const getResearchPlan = (query) => api.post("/research/plan", { query });

// Export research report
export const exportReport = (reportId, format = "markdown") => api.get(`/research/export/${reportId}?format=${format}`);

export default {
  getResearchAgents,
  createResearchReport,
  analyzeConflicts,
  generateEvidence,
  getSynthesis,
  listReports,
  getResearchPlan,
  exportReport,
};
