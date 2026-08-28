import api from "./axios";

// ============================================================================
// Knowledge Layer API
// ============================================================================

// Get knowledge entities
export const getEntities = (documentId) => api.get(`/knowledge/entities/${documentId}`);

// Get knowledge concepts
export const getConcepts = (documentId) => api.get(`/knowledge/concepts/${documentId}`);

// Get knowledge relationships
export const getRelationships = (documentId) => api.get(`/knowledge/relationships/${documentId}`);

// Get document summary
export const getSummary = (documentId) => api.get(`/knowledge/summary/${documentId}`);

// Get extracted questions
export const getQuestions = (documentId) => api.get(`/knowledge/questions/${documentId}`);

// Get flashcards
export const getFlashcards = (documentId) => api.get(`/knowledge/flashcards/${documentId}`);

// Get topics
export const getTopics = (documentId) => api.get(`/knowledge/topics/${documentId}`);

// Get semantic tags
export const getSemanticTags = (documentId) => api.get(`/knowledge/semantic-tags/${documentId}`);

// Search knowledge graph
export const searchKnowledgeGraph = (query) => api.post("/knowledge/search", { query });

// Get knowledge graph visualization
export const getKnowledgeGraph = (documentId) => api.get(`/knowledge/graph/${documentId}`);

// Export knowledge
export const exportKnowledge = (documentId, format = "json") => 
  api.get(`/knowledge/export/${documentId}?format=${format}`);

export default {
  getEntities,
  getConcepts,
  getRelationships,
  getSummary,
  getQuestions,
  getFlashcards,
  getTopics,
  getSemanticTags,
  searchKnowledgeGraph,
  getKnowledgeGraph,
  exportKnowledge,
};
