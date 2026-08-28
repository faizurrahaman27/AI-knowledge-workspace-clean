import { useState, useEffect } from "react";
import { getExams, generateExam, submitExam, getExamResults, getSpacedRepetitionReview } from "../api/exam";
import api from "../api/axios";

const MOCK_EXAMS = [
  { id: 1, title: "Machine Learning Fundamentals", questions: 20, duration: 45, difficulty: "Intermediate" },
  { id: 2, title: "Deep Learning Basics", questions: 15, duration: 30, difficulty: "Beginner" },
  { id: 3, title: "NLP Concepts", questions: 25, duration: 60, difficulty: "Advanced" },
];

export default function Exam() {
  const [loading, setLoading] = useState(true);
  const [exams, setExams] = useState([]);
  const [activeTab, setActiveTab] = useState("exams");
  const [selectedExam, setSelectedExam] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [showResults, setShowResults] = useState(false);
  const [spacedRepReview, setSpacedRepReview] = useState([]);

  useEffect(() => {
    fetchExams();
    fetchSpacedRep();
  }, []);

  const fetchExams = async () => {
    try {
      const res = await getExams();
      setExams(res.data);
    } catch (err) {
      setExams(MOCK_EXAMS);
    } finally {
      setLoading(false);
    }
  };

  const fetchSpacedRep = async () => {
    try {
      const res = await getSpacedRepetitionReview();
      setSpacedRepReview(res.data);
    } catch (err) {
      setSpacedRepReview([]);
    }
  };

  const startExam = (exam) => {
    setSelectedExam(exam);
    setCurrentQuestion(0);
    setAnswers({});
    setShowResults(false);
  };

  const handleAnswer = (questionIndex, answerIndex) => {
    setAnswers({ ...answers, [questionIndex]: answerIndex });
  };

  const submitCurrentExam = async () => {
    if (!selectedExam) return;
    try {
      await submitExam(selectedExam.id, answers);
      setShowResults(true);
    } catch (err) {
      console.log("Using mock results");
      setShowResults(true);
    }
  };

  const MOCK_QUESTIONS = [
    { id: 1, question: "What is the main purpose of regularization in ML?", options: ["Reduce overfitting", "Increase complexity", "Speed up training", "Reduce data"], correct: 0 },
    { id: 2, question: "Which algorithm is commonly used for classification?", options: ["Linear Regression", "K-Means", "Logistic Regression", "PCA"], correct: 2 },
    { id: 3, question: "What is the bias-variance tradeoff?", options: ["High bias = high variance", "Balance between model complexity", "Trade money for accuracy", "None of the above"], correct: 1 },
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold">Exam Preparation</h1>
          <p className="text-slate-400 mt-1">Custom exams, practice questions, and spaced repetition</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-slate-700 pb-2">
          {[
            { key: "exams", label: "Exams", icon: "📝" },
            { key: "practice", label: "Practice Mode", icon: "🎯" },
            { key: "flashcards", label: "Flashcards", icon: "🃏" },
            { key: "progress", label: "Progress", icon: "📊" },
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

        {/* Exams Tab */}
        {activeTab === "exams" && !selectedExam && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(exams.length > 0 ? exams : MOCK_EXAMS).map((exam) => (
              <div key={exam.id} className="bg-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-2">{exam.title}</h3>
                <div className="flex gap-4 text-sm text-slate-400 mb-4">
                  <span>❓ {exam.questions} questions</span>
                  <span>⏱️ {exam.duration} min</span>
                </div>
                <div className="flex items-center gap-2 mb-4">
                  <span className={`px-2 py-1 rounded text-xs ${
                    exam.difficulty === "Beginner" ? "bg-green-500/20 text-green-400" :
                    exam.difficulty === "Intermediate" ? "bg-amber-500/20 text-amber-400" :
                    "bg-red-500/20 text-red-400"
                  }`}>
                    {exam.difficulty}
                  </span>
                </div>
                <button
                  onClick={() => startExam(exam)}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
                >
                  Start Exam
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Exam Taking */}
        {selectedExam && !showResults && (
          <div className="bg-slate-800 rounded-xl p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-semibold">{selectedExam.title}</h3>
              <div className="flex items-center gap-4">
                <span className="text-slate-400">
                  Question {currentQuestion + 1} of {MOCK_QUESTIONS.length}
                </span>
                <button
                  onClick={() => setSelectedExam(null)}
                  className="text-slate-400 hover:text-white"
                >
                  ✕ Exit
                </button>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-700 rounded-full h-2 mb-6">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${((currentQuestion + 1) / MOCK_QUESTIONS.length) * 100}%` }}
              ></div>
            </div>

            {/* Question */}
            <div className="mb-6">
              <p className="text-lg mb-4">{MOCK_QUESTIONS[currentQuestion].question}</p>
              <div className="space-y-3">
                {MOCK_QUESTIONS[currentQuestion].options.map((option, i) => (
                  <button
                    key={i}
                    onClick={() => handleAnswer(currentQuestion, i)}
                    className={`w-full p-4 rounded-lg text-left transition ${
                      answers[currentQuestion] === i
                        ? "bg-blue-600"
                        : "bg-slate-700 hover:bg-slate-600"
                    }`}
                  >
                    <span className="mr-3">{String.fromCharCode(65 + i)}.</span>
                    {option}
                  </button>
                ))}
              </div>
            </div>

            {/* Navigation */}
            <div className="flex justify-between">
              <button
                onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
                disabled={currentQuestion === 0}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 rounded-lg"
              >
                Previous
              </button>
              {currentQuestion < MOCK_QUESTIONS.length - 1 ? (
                <button
                  onClick={() => setCurrentQuestion(currentQuestion + 1)}
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
                >
                  Next
                </button>
              ) : (
                <button
                  onClick={submitCurrentExam}
                  className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                >
                  Submit Exam
                </button>
              )}
            </div>
          </div>
        )}

        {/* Results */}
        {showResults && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-xl font-semibold mb-6">Exam Results</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-slate-700 rounded-xl p-6 text-center">
                <p className="text-4xl font-bold text-green-400 mb-2">80%</p>
                <p className="text-slate-400">Score</p>
              </div>
              <div className="bg-slate-700 rounded-xl p-6 text-center">
                <p className="text-4xl font-bold text-blue-400 mb-2">8/10</p>
                <p className="text-slate-400">Correct Answers</p>
              </div>
              <div className="bg-slate-700 rounded-xl p-6 text-center">
                <p className="text-4xl font-bold text-amber-400 mb-2">12m</p>
                <p className="text-slate-400">Time Taken</p>
              </div>
            </div>

            <h4 className="font-semibold mb-4">Question Review</h4>
            <div className="space-y-3">
              {MOCK_QUESTIONS.map((q, i) => (
                <div key={q.id} className={`p-4 rounded-lg ${
                  answers[i] === q.correct ? "bg-green-500/20" : "bg-red-500/20"
                }`}>
                  <div className="flex justify-between items-start">
                    <p className="font-medium">{q.question}</p>
                    <span className={answers[i] === q.correct ? "text-green-400" : "text-red-400"}>
                      {answers[i] === q.correct ? "✓" : "✗"}
                    </span>
                  </div>
                  {answers[i] !== q.correct && (
                    <p className="text-sm text-slate-400 mt-2">
                      Correct: {q.options[q.correct]}
                    </p>
                  )}
                </div>
              ))}
            </div>

            <button
              onClick={() => setSelectedExam(null)}
              className="mt-6 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg"
            >
              Back to Exams
            </button>
          </div>
        )}

        {/* Practice Mode */}
        {activeTab === "practice" && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Practice Mode</h3>
            <p className="text-slate-400 mb-6">
              Test your knowledge with random questions from your documents.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {["Easy", "Medium", "Hard", "Random"].map((level, i) => (
                <button
                  key={level}
                  className="p-6 bg-slate-700 hover:bg-slate-600 rounded-xl text-center"
                >
                  <p className="text-2xl mb-2">
                    {i === 0 ? "🌱" : i === 1 ? "⚡" : i === 2 ? "🔥" : "🎲"}
                  </p>
                  <p className="font-medium">{level}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Flashcards */}
        {activeTab === "flashcards" && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Spaced Repetition Review</h3>
            <p className="text-slate-400 mb-6">
              Review flashcards based on your learning schedule.
            </p>
            {spacedRepReview.length > 0 ? (
              <div className="space-y-4">
                {spacedRepReview.map((card) => (
                  <div key={card.id} className="p-4 bg-slate-700 rounded-lg">
                    <p className="font-medium">{card.front}</p>
                    <p className="text-slate-400 mt-2">{card.back}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-slate-500 text-center py-12">
                No cards to review right now. Check back later!
              </p>
            )}
          </div>
        )}

        {/* Progress */}
        {activeTab === "progress" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-800 rounded-xl p-6">
                <p className="text-3xl font-bold">24</p>
                <p className="text-slate-400">Exams Completed</p>
              </div>
              <div className="bg-slate-800 rounded-xl p-6">
                <p className="text-3xl font-bold">87%</p>
                <p className="text-slate-400">Average Score</p>
              </div>
              <div className="bg-slate-800 rounded-xl p-6">
                <p className="text-3xl font-bold">156</p>
                <p className="text-slate-400">Cards Reviewed</p>
              </div>
            </div>
            <div className="bg-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Learning Streak</h3>
              <div className="flex gap-2">
                {[...Array(14)].map((_, i) => (
                  <div
                    key={i}
                    className={`w-8 h-8 rounded ${
                      i < 10 ? "bg-green-500" : "bg-slate-700"
                    }`}
                  />
                ))}
              </div>
              <p className="text-sm text-slate-400 mt-4">10-day streak! Keep it up!</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
