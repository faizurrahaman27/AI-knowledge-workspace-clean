import api from "./axios";

// === Teams ===

export async function createTeam(name) {
  return (await api.post("/teams/", { name })).data;
}

export async function listTeams() {
  return (await api.get("/teams/")).data;
}

export async function inviteToTeam(teamId, email, role = "member") {
  return (await api.post(`/teams/${teamId}/invite`, { email, role })).data;
}

export async function acceptInvite(email, token) {
  return (await api.post("/teams/accept-invite", { email, token })).data;
}

export async function listTeamMembers(teamId) {
  return (await api.get(`/teams/${teamId}/members`)).data;
}

// === Workspaces ===

export async function createWorkspace(data) {
  return (await api.post("/workspaces/", data)).data;
}

export async function updateWorkspace(workspaceId, data) {
  return (await api.patch(`/workspaces/${workspaceId}`, data)).data;
}

export async function listWorkspaces(params = {}) {
  const { status, favorites, include_team, limit, offset } = params;
  const queryParams = new URLSearchParams();
  if (status) queryParams.append("status", status);
  if (favorites) queryParams.append("favorites", "true");
  if (include_team === false) queryParams.append("include_team", "false");
  if (limit) queryParams.append("limit", limit);
  if (offset) queryParams.append("offset", offset);
  
  const query = queryParams.toString();
  return (await api.get(`/workspaces/${query ? `?${query}` : ""}`)).data;
}

export async function listRecentWorkspaces(limit = 10) {
  return (await api.get(`/workspaces/recent?limit=${limit}`)).data;
}

export async function searchWorkspaces(query, includeArchived = false) {
  return (await api.get(`/workspaces/search?q=${encodeURIComponent(query)}&include_archived=${includeArchived}`)).data;
}

export async function getDefaultWorkspace() {
  return (await api.get("/workspaces/default")).data;
}

export async function getWorkspace(workspaceId) {
  return (await api.get(`/workspaces/${workspaceId}`)).data;
}

export async function deleteWorkspace(workspaceId, permanent = false) {
  return (await api.delete(`/workspaces/${workspaceId}?permanent=${permanent}`)).data;
}

export async function archiveWorkspace(workspaceId) {
  return (await api.post(`/workspaces/${workspaceId}/archive`)).data;
}

export async function restoreWorkspace(workspaceId) {
  return (await api.post(`/workspaces/${workspaceId}/restore`)).data;
}

export async function toggleFavoriteWorkspace(workspaceId) {
  return (await api.post(`/workspaces/${workspaceId}/favorite`)).data;
}

export async function addTagToWorkspace(workspaceId, tag) {
  return (await api.post(`/workspaces/${workspaceId}/tags`, { tag })).data;
}

export async function removeTagFromWorkspace(workspaceId, tag) {
  return (await api.delete(`/workspaces/${workspaceId}/tags/${encodeURIComponent(tag)}`)).data;
}

export async function addDocumentToWorkspace(workspaceId, documentId) {
  return (await api.post(`/workspaces/${workspaceId}/documents`, { document_id: documentId })).data;
}

export async function removeDocumentFromWorkspace(workspaceId, documentId) {
  return (await api.delete(`/workspaces/${workspaceId}/documents/${documentId}`)).data;
}

export async function listWorkspaceDocuments(workspaceId) {
  return (await api.get(`/workspaces/${workspaceId}/documents`)).data;
}

// === Upload ===

export async function uploadFile(file, workspaceId = null) {
  const formData = new FormData();
  formData.append("file", file);
  if (workspaceId) formData.append("workspace_id", workspaceId);
  
  return (await api.post("/upload/file", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })).data;
}

export async function uploadMultipleFiles(files, workspaceId = null) {
  const formData = new FormData();
  files.forEach((file, index) => {
    formData.append("files", file);
  });
  if (workspaceId) formData.append("workspace_id", workspaceId);
  
  return (await api.post("/upload/files", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })).data;
}

export async function uploadScan(file, languageCode = null, workspaceId = null) {
  const formData = new FormData();
  formData.append("file", file);
  if (languageCode) formData.append("language_code", languageCode);
  if (workspaceId) formData.append("workspace_id", workspaceId);
  
  return (await api.post("/upload/scan", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })).data;
}

export async function importFromURL(url, sourceType = "web_page", workspaceId = null) {
  return (await api.post("/upload/url", {
    url,
    source_type: sourceType,
    workspace_id: workspaceId,
  })).data;
}

export async function importFromGitHub(url, workspaceId = null) {
  return (await api.post("/upload/github", null, {
    params: { url, workspace_id: workspaceId },
  })).data;
}

// === Agent / Study Pack ===

export async function generateStudyPack(documentId) {
  return (
    await api.post("/agent/study-pack", {
      document_id: documentId,
      request_text: "full study pack",
    })
  ).data;
}

export async function downloadStudyPackPdf(documentId, suggestedFilename) {
  const response = await api.get(`/agent/study-pack/${documentId}/pdf`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = suggestedFilename || `study_pack_${documentId}.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// === Activity ===

export async function getActivityHistory() {
  return (await api.get("/activity/history")).data;
}

export async function getSuggestions() {
  return (await api.get("/activity/suggestions")).data;
}
