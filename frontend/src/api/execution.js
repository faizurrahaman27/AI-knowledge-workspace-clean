import api from "./axios";

// ============================================================================
// Execution API (Phase 10)
// ============================================================================

// Execute a single action
export const executeAction = (data) => api.post("/execution/run", data);

// Execute a workflow
export const executeWorkflow = (data) => api.post("/execution/workflow", data);

// Get execution status
export const getExecution = (executionId) => api.get(`/execution/${executionId}`);

// Get execution outputs
export const getExecutionOutputs = (executionId) => api.get(`/execution/${executionId}/outputs`);

// Download execution output
export const downloadOutput = (executionId, filename) => 
  api.get(`/execution/${executionId}/outputs/${filename}`, { responseType: 'blob' });

// Get execution history
export const getExecutionHistory = (params = {}) => api.get("/execution/history", { params });

// Cancel execution
export const cancelExecution = (executionId) => api.post(`/execution/${executionId}/cancel`);

// Retry execution
export const retryExecution = (executionId) => api.post(`/execution/${executionId}/retry`);

// Get available templates
export const getTemplates = () => api.get("/execution/templates");

// Get system status
export const getExecutionStatus = () => api.get("/execution/status");

// Cleanup old outputs
export const cleanupOutputs = (maxAgeHours = 24) => api.post("/execution/cleanup", null, {
  params: { max_age_hours: maxAgeHours }
});

// Get output file URL
export const getOutputUrl = (executionId, filename) => {
  return `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}/execution/${executionId}/outputs/${filename}`;
};

export default {
  executeAction,
  executeWorkflow,
  getExecution,
  getExecutionOutputs,
  downloadOutput,
  getExecutionHistory,
  cancelExecution,
  retryExecution,
  getTemplates,
  getExecutionStatus,
  cleanupOutputs,
  getOutputUrl,
};
