import api from "./axios";

// ============================================================================
// Jobs API
// ============================================================================

// Get available jobs
export const getJobs = (params = {}) => api.get("/jobs/", { params });

// Get job by ID
export const getJob = (jobId) => api.get(`/jobs/${jobId}`);

// Search jobs
export const searchJobs = (query) => api.post("/jobs/search", { query });

// Apply to job
export const applyToJob = (jobId, data) => api.post(`/jobs/${jobId}/apply`, data);

// Track job application
export const trackApplication = (applicationId) => api.get(`/jobs/applications/${applicationId}`);

// Get job recommendations
export const getJobRecommendations = (resumeId) => api.get(`/jobs/recommendations/${resumeId}`);

export default {
  getJobs,
  getJob,
  searchJobs,
  applyToJob,
  trackApplication,
  getJobRecommendations,
};
