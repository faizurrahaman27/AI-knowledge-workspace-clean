import { useState } from "react";
import api from "../api/axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const MODES = [
  { value: "summary", label: "Summarize" },
  { value: "important_questions", label: "Important Questions" },
  { value: "quiz", label: "Quiz (MCQs)" },
  { value: "flashcards", label: "Flashcards" },
  { value: "revision_notes", label: "Revision Notes" },
  { value: "cheat_sheet", label: "Cheat Sheet" },
];

export default function StudyPanel({ selectedDocument }) {
  const [loadingMode, setLoadingMode] = useState(null);
  const [content, setContent] = useState(null);

  const run = async (mode) => {
    if (!selectedDocument) {
      alert("Select a document first.");
      return;
    }
    setLoadingMode(mode);
    setContent(null);
    try {
      const response = await api.post("/study/", {
        document_id: selectedDocument.id,
        mode,
      });
      setContent(response.data.content);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Study generation failed.");
    } finally {
      setLoadingMode(null);
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-xl font-semibold text-white mb-1">Study Mode</h2>
      <p className="text-slate-400 text-sm mb-4">
        Generate study material from the whole document, instantly.
      </p>

      <div className="flex flex-wrap gap-2">
        {MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => run(m.value)}
            disabled={loadingMode !== null}
            className="bg-slate-700 hover:bg-blue-600 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
          >
            {loadingMode === m.value ? "Generating..." : m.label}
          </button>
        ))}
      </div>

      {content && (
        <div className="mt-6 bg-slate-900 rounded-lg p-4 prose prose-invert max-w-none prose-sm" dir="auto">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
