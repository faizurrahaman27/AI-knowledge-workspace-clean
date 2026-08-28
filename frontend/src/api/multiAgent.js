import api from "./axios";

// ============================================================================
// Multi-Agent & Orchestration API
// ============================================================================

// Get available agents
export const getAgents = () => api.get("/multi-agent/agents");

// Get agent by ID
export const getAgent = (agentId) => api.get(`/multi-agent/agents/${agentId}`);

// Execute agent
export const executeAgent = (agentId, data) => api.post(`/multi-agent/agents/${agentId}/execute`, data);

// Get agent capabilities
export const getAgentCapabilities = (agentId) => api.get(`/multi-agent/agents/${agentId}/capabilities`);

// Create team
export const createTeam = (data) => api.post("/multi-agent/team", data);

// Get teams
export const getTeams = () => api.get("/multi-agent/teams");

// Get team by ID
export const getTeam = (teamId) => api.get(`/multi-agent/team/${teamId}`);

// Add agent to team
export const addAgentToTeam = (teamId, agentId) => api.post(`/multi-agent/team/${teamId}/agents`, { agent_id: agentId });

// Remove agent from team
export const removeAgentFromTeam = (teamId, agentId) => api.delete(`/multi-agent/team/${teamId}/agents/${agentId}`);

// Execute team
export const executeTeam = (teamId, data) => api.post(`/multi-agent/team/${teamId}/execute`, data);

// Get orchestration status
export const getOrchestrationStatus = () => api.get("/orchestration/status");

// Get orchestration metrics
export const getOrchestrationMetrics = () => api.get("/orchestration/metrics");

// Get orchestration workflows
export const getOrchestrationWorkflows = () => api.get("/orchestration/workflows");

// Execute orchestration workflow
export const executeOrchestrationWorkflow = (workflowId, data) => 
  api.post(`/orchestration/workflows/${workflowId}/execute`, data);

// Get workflow status
export const getWorkflowStatus = (workflowId) => api.get(`/orchestration/workflows/${workflowId}/status`);

export default {
  getAgents,
  getAgent,
  executeAgent,
  getAgentCapabilities,
  createTeam,
  getTeams,
  getTeam,
  addAgentToTeam,
  removeAgentFromTeam,
  executeTeam,
  getOrchestrationStatus,
  getOrchestrationMetrics,
  getOrchestrationWorkflows,
  executeOrchestrationWorkflow,
  getWorkflowStatus,
};
