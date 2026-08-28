import api from "./axios";

// ============================================================================
// Integration API (Phase 8.1)
// ============================================================================

// Get integration status
export const getIntegrationStatus = () => api.get("/integration/status");

// Get connected services
export const getConnectedServices = () => api.get("/integration/services");

// Connect service
export const connectService = (serviceId, credentials) => 
  api.post("/integration/services/connect", { service_id: serviceId, credentials });

// Disconnect service
export const disconnectService = (serviceId) => api.delete(`/integration/services/${serviceId}`);

// Get available integrations
export const getAvailableIntegrations = () => api.get("/integration/available");

// Get integration events
export const getIntegrationEvents = (params = {}) => api.get("/integration/events", { params });

// Get event details
export const getEventDetails = (eventId) => api.get(`/integration/events/${eventId}`);

// Get pipeline status
export const getPipelineStatus = (documentId) => api.get(`/integration/pipeline/${documentId}`);

// Trigger pipeline
export const triggerPipeline = (documentId, steps = []) => api.post("/integration/pipeline/trigger", {
  document_id: documentId,
  steps
});

// Get autonomous learning status
export const getAutonomousStatus = () => api.get("/integration/autonomous/status");

// Get learning suggestions
export const getLearningSuggestions = (documentId) => api.get(`/integration/autonomous/suggestions/${documentId}`);

// Apply learning suggestion
export const applySuggestion = (suggestionId) => api.post(`/integration/autonomous/apply/${suggestionId}`);

export default {
  getIntegrationStatus,
  getConnectedServices,
  connectService,
  disconnectService,
  getAvailableIntegrations,
  getIntegrationEvents,
  getEventDetails,
  getPipelineStatus,
  triggerPipeline,
  getAutonomousStatus,
  getLearningSuggestions,
  applySuggestion,
};
