import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { generateStudyPack, downloadStudyPackPdf } from "../api/workspace";

const SECTIONS = [
  { key: "summary", label: "Summary" },
  { key: "important_questions", label: "Important Questions" },
  { key: "flashcards", label: "Flashcards" },
  { key: "quiz", label: "Quiz" },
];

export default function StudyPackPanel({ selectedDocument }) {
  const [pack, setPack] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  const generate = async () => {
    if (!selectedDocument) {
      alert("Select a document first.");
      return;
    }
    setLoading(true);
    setError("");
    setPack(null);
    try {
      const data = await generateStudyPack(selectedDocument.id);
      setPack(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not generate the study pack.");
    } finally {
      setLoading(false);
    }
  };

  const download = async () => {
    if (!selectedDocument) return;
    setDownloading(true);
    try {
      await downloadStudyPackPdf(selectedDocument.id, `study_pack_${selectedDocument.filename}.pdf`);
    } catch (err) {
      alert(err.response?.data?.detail || "Download failed.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-xl font-semibold text-white mb-1">AI Agent: Full Study Pack</h2>
      <p className="text-slate-400 text-sm mb-4">
        A chained workflow — Summary → Important Questions → Flashcards → Quiz → Mind Map — run in
        one click for the whole document, exportable as a single PDF.
      </p>

      <div className="flex flex-wrap gap-3">
        <button
          onClick={generate}
          disabled={loading}
          className="bg-green-600 hover:bg-green-700 px-6 py-2 rounded-lg text-white disabled:opacity-50"
        >
          {loading ? "Generating (this runs 4-5 LLM calls, may take a bit)..." : "Generate Study Pack"}
        </button>

        <button
          onClick={download}
          disabled={downloading || !selectedDocument}
          className="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded-lg text-white disabled:opacity-50"
        >
          {downloading ? "Preparing PDF..." : "📄 Download as PDF"}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm mt-3">{error}</p>}

      {pack && (
        <div className="mt-6 space-y-6">
          {SECTIONS.map((section) => (
            <div key={section.key} className="bg-slate-900 rounded-lg p-4">
              <h3 className="text-white font-semibold mb-2">{section.label}</h3>
              <div className="prose prose-invert max-w-none prose-sm" dir="auto">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{pack[section.key]}</ReactMarkdown>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
