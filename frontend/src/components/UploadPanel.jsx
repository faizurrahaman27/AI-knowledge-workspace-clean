import { useState } from "react";
import api from "../api/axios";

const MODES = [
  { key: "pdf", label: "Upload PDF" },
  { key: "url", label: "From Website" },
  { key: "github", label: "From GitHub" },
];

export default function UploadPanel({ fetchDocuments }) {
  const [mode, setMode] = useState("pdf");
  const [selectedFile, setSelectedFile] = useState(null);
  const [urlInput, setUrlInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleUploadPdf = async () => {
    if (!selectedFile) {
      setError("Please choose a PDF first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      setLoading(true);
      setError("");
      await api.post("/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setSelectedFile(null);
      fetchDocuments();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleIngestUrl = async (endpoint) => {
    if (!urlInput.trim()) {
      setError("Please enter a URL.");
      return;
    }
    try {
      setLoading(true);
      setError("");
      await api.post(endpoint, { url: urlInput.trim() });
      setUrlInput("");
      fetchDocuments();
    } catch (err) {
      setError(err.response?.data?.detail || "Import failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6 sm:p-8">
      <h2 className="text-2xl font-semibold text-white">Add a Document</h2>

      <div className="mt-4 flex gap-2 flex-wrap">
        {MODES.map((m) => (
          <button
            key={m.key}
            onClick={() => {
              setMode(m.key);
              setError("");
            }}
            className={`px-3 py-1.5 rounded-lg text-sm ${
              mode === m.key ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-300"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {mode === "pdf" && (
        <div className="mt-4">
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setSelectedFile(e.target.files[0])}
            className="text-sm text-slate-300"
          />
          {selectedFile && (
            <p className="mt-2 text-green-400 text-sm">Selected: {selectedFile.name}</p>
          )}
          <button
            onClick={handleUploadPdf}
            disabled={loading}
            className="mt-4 bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg text-white disabled:opacity-50 block"
          >
            {loading ? "Uploading..." : "Upload PDF"}
          </button>
        </div>
      )}

      {mode === "url" && (
        <div className="mt-4">
          <p className="text-slate-400 text-sm mb-2">
            Imports the readable article text from a web page (strips nav/ads/boilerplate).
          </p>
          <input
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://example.com/some-article"
            className="w-full p-3 rounded-lg bg-slate-700 text-white text-sm outline-none"
          />
          <button
            onClick={() => handleIngestUrl("/documents/from-url")}
            disabled={loading}
            className="mt-4 bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg text-white disabled:opacity-50 block"
          >
            {loading ? "Importing..." : "Import Web Page"}
          </button>
        </div>
      )}

      {mode === "github" && (
        <div className="mt-4">
          <p className="text-slate-400 text-sm mb-2">
            Imports a single file from a public GitHub repo (README, docs, source file) — not a
            whole-repo crawler, one file at a time.
          </p>
          <input
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://github.com/owner/repo/blob/main/README.md"
            className="w-full p-3 rounded-lg bg-slate-700 text-white text-sm outline-none"
          />
          <button
            onClick={() => handleIngestUrl("/documents/from-github")}
            disabled={loading}
            className="mt-4 bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg text-white disabled:opacity-50 block"
          >
            {loading ? "Importing..." : "Import GitHub File"}
          </button>
        </div>
      )}

      {error && <p className="mt-3 text-red-400 text-sm">{error}</p>}
    </div>
  );
}
