import api from "./axios";

// ============================================================================
// Math API
// ============================================================================

// Solve math problem
export const solveMath = (problem) => api.post("/math/solve", { problem });

// Generate math explanation
export const explainMath = (problem) => api.post("/math/explain", { problem });

// Generate math visualization
export const visualizeMath = (problem) => api.post("/math/visualize", { problem });

// Generate step-by-step solution
export const mathStepByStep = (problem) => api.post("/math/steps", { problem });

// Check math answer
export const checkMathAnswer = (problem, answer) => api.post("/math/check", { problem, answer });

// Generate practice problems
export const generatePractice = (topic, count = 5) => api.post("/math/practice", { topic, count });

export default {
  solveMath,
  explainMath,
  visualizeMath,
  mathStepByStep,
  checkMathAnswer,
  generatePractice,
};
