import api from "./axios";

// ============================================================================
// Video API
// ============================================================================

// Get video transcripts
export const getTranscripts = (videoId) => api.get(`/video/transcripts/${videoId}`);

// Get video summary
export const getVideoSummary = (videoId) => api.get(`/video/summary/${videoId}`);

// Get video flashcards
export const getVideoFlashcards = (videoId) => api.get(`/video/flashcards/${videoId}`);

// Process video
export const processVideo = (videoId) => api.post(`/video/process/${videoId}`);

// Get processing status
export const getProcessingStatus = (videoId) => api.get(`/video/status/${videoId}`);

// Generate video quiz
export const generateVideoQuiz = (videoId) => api.post(`/video/quiz/${videoId}`);

export default {
  getTranscripts,
  getVideoSummary,
  getVideoFlashcards,
  processVideo,
  getProcessingStatus,
  generateVideoQuiz,
};
