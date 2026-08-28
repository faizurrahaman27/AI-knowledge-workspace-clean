import { useState } from "react";
import { API_BASE_URL } from "../api/axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ComparePanel({ documents }) {
  const [docA, setDocA] = useState("");
  const [docB, setDocB] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [steps, setSteps] = useState([]);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!docA || !docB || docA === docB) {
      alert("Pick two different documents.");
      return;
    }
    if (!question.trim()) return;

    setLoading(true);
    setAnswer("");
    setSteps([]);

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/compare/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          document_id_a: Number(docA),
          document_id_b: Number(docB),
          question,
        }),
      });

      if (response.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/";
        return;
      }

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Comparison failed.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;
          let event;
          try {
            event = JSON.parse(line);
          } catch {
            continue;
          }
          if (event.type === "status") {
            setSteps((prev) => [...prev, event.label]);
          } else if (event.type === "token") {
            setAnswer((prev) => prev + event.text);
          }
        }
      }
    } catch (err) {
      console.error(err);
      setAnswer(`❌ ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-xl font-semibold text-white mb-1">Compare Documents</h2>
      <p className="text-slate-400 text-sm mb-4">
        Ask a question that spans two documents — e.g. "what's different between these two?"
      </p>

      <div className="flex flex-wrap gap-3">
        <select value={docA} onChange={(e) => setDocA(e.target.value)} className="bg-slate-700 text-white text-sm rounded-lg px-3 py-2">
          <option value="">Document A...</option>
          {documents.map((d) => (
            <option key={d.id} value={d.id}>{d.filename}</option>
          ))}
        </select>

        <select value={docB} onChange={(e) => setDocB(e.target.value)} className="bg-slate-700 text-white text-sm rounded-lg px-3 py-2">
          <option value="">Document B...</option>
          {documents.map((d) => (
            <option key={d.id} value={d.id}>{d.filename}</option>
          ))}
        </select>
      </div>

      <textarea
        rows={2}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="What would you like to compare?"
        className="w-full mt-3 p-3 rounded-lg bg-slate-700 text-white outline-none text-sm"
      />

      <button
        onClick={run}
        disabled={loading}
        className="mt-3 bg-green-600 hover:bg-green-700 px-6 py-2 rounded-lg text-white disabled:opacity-50"
      >
        {loading ? "Comparing..." : "Compare"}
      </button>

      {steps.length > 0 && (
        <div className="mt-4 text-xs text-slate-400 space-y-1">
          {steps.map((s, i) => <div key={i}>⏳ {s}</div>)}
        </div>
      )}

      {answer && (
        <div className="mt-4 bg-slate-900 rounded-lg p-4 prose prose-invert max-w-none prose-sm" dir="auto">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
