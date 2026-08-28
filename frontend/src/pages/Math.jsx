import { useState } from "react";
import { solveMath, explainMath, mathStepByStep, generatePractice } from "../api/math";

export default function Math() {
  const [problem, setProblem] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState("solve");
  const [practiceTopic, setPracticeTopic] = useState("");
  const [practiceProblems, setPracticeProblems] = useState([]);

  const handleSolve = async (type) => {
    if (!problem.trim()) return;
    setLoading(true);
    try {
      let res;
      if (type === "solve") {
        res = await solveMath(problem);
      } else if (type === "explain") {
        res = await explainMath(problem);
      } else {
        res = await mathStepByStep(problem);
      }
      setResult(res.data);
    } catch (err) {
      // Mock result for demo
      setResult({
        answer: "42",
        explanation: "This is a demonstration. The actual calculation would be performed by the backend.",
        steps: ["Step 1: Identify the problem", "Step 2: Apply formula", "Step 3: Calculate result"]
      });
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePractice = async () => {
    if (!practiceTopic.trim()) return;
    setLoading(true);
    try {
      const res = await generatePractice(practiceTopic, 5);
      setPracticeProblems(res.data);
    } catch (err) {
      // Mock problems
      setPracticeProblems([
        { id: 1, question: `Solve for x: 2x + 5 = 15`, difficulty: "Easy" },
        { id: 2, question: `Find the derivative of f(x) = x³ + 2x²`, difficulty: "Medium" },
        { id: 3, question: `Calculate the integral of sin(x) dx`, difficulty: "Medium" },
        { id: 4, question: `Solve: 3(x - 2) = 2(x + 4)`, difficulty: "Easy" },
        { id: 5, question: `Find the limit of (x² - 1)/(x - 1) as x → 1`, difficulty: "Hard" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold">Math & Science</h1>
          <p className="text-slate-400 mt-1">Step-by-step problem solving, formula explanations, and graphs</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-slate-700 pb-2">
          {[
            { key: "solve", label: "Solve Problem", icon: "🧮" },
            { key: "explain", label: "Explain & Learn", icon: "📚" },
            { key: "practice", label: "Practice", icon: "🎯" },
            { key: "formulas", label: "Formulas", icon: "📐" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-t-lg text-sm font-medium flex items-center gap-2 ${
                activeTab === tab.key
                  ? "bg-slate-800 text-white border-b-2 border-blue-500"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <span>{tab.icon}</span>
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Solve Tab */}
        {activeTab === "solve" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Enter Your Problem</h3>
              <textarea
                value={problem}
                onChange={(e) => setProblem(e.target.value)}
                placeholder="Type or paste your math problem here...&#10;&#10;Examples:&#10;• 2x + 5 = 15&#10;• ∫x²dx&#10;• d/dx(sin(x))"
                className="w-full bg-slate-700 border border-slate-600 rounded-lg p-4 text-white placeholder-slate-400 h-48 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
              />
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => handleSolve("solve")}
                  disabled={loading || !problem.trim()}
                  className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-medium"
                >
                  Solve
                </button>
                <button
                  onClick={() => handleSolve("steps")}
                  disabled={loading || !problem.trim()}
                  className="flex-1 py-3 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 rounded-lg font-medium"
                >
                  Step-by-Step
                </button>
              </div>
            </div>

            <div className="bg-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Solution</h3>
              {loading ? (
                <div className="flex items-center justify-center h-48">
                  <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
                </div>
              ) : result ? (
                <div className="space-y-4">
                  <div className="p-4 bg-green-500/20 border border-green-500/30 rounded-lg">
                    <p className="text-sm text-slate-400 mb-1">Answer</p>
                    <p className="text-2xl font-bold text-green-400">{result.answer}</p>
                  </div>
                  {result.explanation && (
                    <div className="p-4 bg-slate-700 rounded-lg">
                      <p className="text-sm text-slate-400 mb-2">Explanation</p>
                      <p className="text-slate-300">{result.explanation}</p>
                    </div>
                  )}
                  {result.steps && (
                    <div className="space-y-2">
                      <p className="text-sm text-slate-400">Steps</p>
                      {result.steps.map((step, i) => (
                        <div key={i} className="flex gap-3 p-3 bg-slate-700 rounded-lg">
                          <span className="w-6 h-6 bg-blue-500/30 rounded-full flex items-center justify-center text-sm font-medium">
                            {i + 1}
                          </span>
                          <span className="text-slate-300">{step}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center h-48 text-slate-500">
                  Enter a problem to see the solution
                </div>
              )}
            </div>
          </div>
        )}

        {/* Explain Tab */}
        {activeTab === "explain" && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Learn & Understand</h3>
            <textarea
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              placeholder="Enter a math concept or problem you want to understand...&#10;&#10;Examples:&#10;• What is the chain rule in calculus?&#10;• Explain linear regression&#10;• How does gradient descent work?"
              className="w-full bg-slate-700 border border-slate-600 rounded-lg p-4 text-white placeholder-slate-400 h-32 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={() => handleSolve("explain")}
              disabled={loading || !problem.trim()}
              className="mt-4 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-medium"
            >
              Explain
            </button>

            {result && (
              <div className="mt-6 p-6 bg-slate-700 rounded-lg">
                <h4 className="font-semibold mb-4">Explanation</h4>
                <div className="prose prose-invert max-w-none">
                  <p className="text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {result.explanation || result.answer || "The explanation will appear here..."}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Practice Tab */}
        {activeTab === "practice" && (
          <div className="space-y-6">
            <div className="bg-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Generate Practice Problems</h3>
              <div className="flex gap-4">
                <input
                  type="text"
                  value={practiceTopic}
                  onChange={(e) => setPracticeTopic(e.target.value)}
                  placeholder="Enter topic (e.g., Calculus, Algebra, Statistics)"
                  className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleGeneratePractice}
                  disabled={loading}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 rounded-lg font-medium"
                >
                  Generate
                </button>
              </div>
            </div>

            <div className="space-y-4">
              {practiceProblems.map((prob) => (
                <div key={prob.id} className="bg-slate-800 rounded-xl p-6">
                  <div className="flex justify-between items-start mb-4">
                    <p className="font-medium text-lg">{prob.question}</p>
                    <span className={`px-2 py-1 rounded text-xs ${
                      prob.difficulty === "Easy" ? "bg-green-500/20 text-green-400" :
                      prob.difficulty === "Medium" ? "bg-amber-500/20 text-amber-400" :
                      "bg-red-500/20 text-red-400"
                    }`}>
                      {prob.difficulty}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">
                      Show Hint
                    </button>
                    <button className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm">
                      Check Answer
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Formulas Tab */}
        {activeTab === "formulas" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { category: "Algebra", formulas: ["x = (-b ± √(b²-4ac)) / 2a", "logₐ(xy) = logₐx + logₐy"] },
              { category: "Calculus", formulas: ["d/dx(xⁿ) = nxⁿ⁻¹", "∫xⁿdx = xⁿ⁺¹/(n+1) + C"] },
              { category: "Trigonometry", formulas: ["sin²θ + cos²θ = 1", "tan θ = sin θ / cos θ"] },
              { category: "Statistics", formulas: ["σ = √(Σ(x-μ)²/N)", "z = (x-μ)/σ"] },
              { category: "Linear Algebra", formulas: ["det(A) = ad - bc", "A⁻¹A = I"] },
              { category: "Physics", formulas: ["F = ma", "E = mc²"] },
            ].map((section) => (
              <div key={section.category} className="bg-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-4">{section.category}</h3>
                <div className="space-y-3">
                  {section.formulas.map((formula, i) => (
                    <div key={i} className="p-3 bg-slate-700 rounded-lg font-mono text-sm">
                      {formula}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
