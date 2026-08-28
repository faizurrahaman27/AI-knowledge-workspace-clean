import api from "./axios";

// ============================================================================
// Exam API
// ============================================================================

// Get available exams
export const getExams = () => api.get("/exam/");

// Get exam by ID
export const getExam = (examId) => api.get(`/exam/${examId}`);

// Generate exam from document
export const generateExam = (documentId, params = {}) => api.post("/exam/generate", {
  document_id: documentId,
  ...params
});

// Submit exam answers
export const submitExam = (examId, answers) => api.post(`/exam/${examId}/submit`, { answers });

// Get exam results
export const getExamResults = (examId) => api.get(`/exam/${examId}/results`);

// Get spaced repetition review
export const getSpacedRepetitionReview = () => api.get("/exam/spaced-repetition");

// Mark item reviewed
export const markReviewed = (itemId) => api.post(`/exam/reviewed/${itemId}`);

export default {
  getExams,
  getExam,
  generateExam,
  submitExam,
  getExamResults,
  getSpacedRepetitionReview,
  markReviewed,
};
