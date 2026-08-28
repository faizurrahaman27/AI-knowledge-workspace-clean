import { useEffect, useState } from "react";
import api from "../api/axios";
import { getSpeechTag, pickVoiceForLang, LANGUAGE_DISPLAY_NAMES } from "../utils/speechLang";

export default function ScanPanel({ fetchDocuments }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [voices, setVoices] = useState([]);
  const [voiceIndex, setVoiceIndex] = useState(null);
  const [ocrLanguage, setOcrLanguage] = useState(""); // "" = auto-detect

  useEffect(() => {
    const loadVoices = () => setVoices(window.speechSynthesis?.getVoices() || []);
    loadVoices();
    window.speechSynthesis?.addEventListener("voiceschanged", loadVoices);
    return () => window.speechSynthesis?.removeEventListener("voiceschanged", loadVoices);
  }, []);

  const handleFile = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setSaved(false);
  };

  const scan = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    if (ocrLanguage) formData.append("language_code", ocrLanguage);

    try {
      const response = await api.post("/scan/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(response.data);

      // Auto-pick a voice matching the detected/chosen language, so
      // "Read Aloud" doesn't mispronounce non-English text by default --
      // still overridable via the dropdown below.
      const tag = getSpeechTag(response.data.language_code);
      const match = pickVoiceForLang(window.speechSynthesis?.getVoices() || [], tag);
      setVoiceIndex(match ? voices.indexOf(match) : null);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Scan failed.");
    } finally {
      setLoading(false);
    }
  };

  const analyzeVisual = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await api.post("/scan/understand-visual", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult({
        extracted_text: "",
        summary: response.data.description,
        language_code: "en",
        language_name: "English",
      });
    } catch (err) {
      console.error(err);
      alert(
        err.response?.data?.detail ||
          "Visual analysis failed. Requires a vision-capable model configured on the server."
      );
    } finally {
      setLoading(false);
    }
  };

  const saveAsDocument = async () => {
    if (!file) return;
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (ocrLanguage) formData.append("language_code", ocrLanguage);

      await api.post("/documents/from-image", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setSaved(true);
      fetchDocuments?.();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Could not save this scan as a document.");
    } finally {
      setSaving(false);
    }
  };

  const speakSummary = () => {
    if (!result) return;
    if (!("speechSynthesis" in window)) {
      alert("Voice output isn't supported in this browser.");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(result.summary);
    utterance.lang = getSpeechTag(result.language_code);
    if (voiceIndex !== null && voices[voiceIndex]) utterance.voice = voices[voiceIndex];
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-xl font-semibold text-white mb-1">Scan &amp; Listen</h2>
      <p className="text-slate-400 text-sm mb-4">
        Upload a photo of a receipt, note, whiteboard, book page, or ID in any supported
        language — it'll extract the text (OCR) and read out what's useful, in that language.
      </p>

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="file"
          accept="image/jpeg,image/jpg,image/png,image/bmp,image/tiff,image/webp"
          onChange={handleFile}
          className="text-sm text-slate-300"
        />

        <select
          value={ocrLanguage}
          onChange={(e) => setOcrLanguage(e.target.value)}
          className="bg-slate-700 text-white text-sm rounded-lg px-2 py-1"
          title="Tell it the language for better OCR accuracy, or leave on auto-detect"
        >
          <option value="">Auto-detect language</option>
          {Object.entries(LANGUAGE_DISPLAY_NAMES).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {preview && (
        <img src={preview} alt="preview" className="mt-2 max-h-64 rounded-lg border border-slate-700" />
      )}

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          onClick={scan}
          disabled={!file || loading}
          className="bg-green-600 hover:bg-green-700 px-6 py-2 rounded-lg text-white disabled:opacity-50"
        >
          {loading ? "Scanning..." : "Scan Image (OCR)"}
        </button>

        <button
          onClick={analyzeVisual}
          disabled={!file || loading}
          className="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded-lg text-white disabled:opacity-50"
          title="For diagrams, charts, flowcharts -- requires a vision-capable model"
        >
          Analyze as Diagram/Chart
        </button>
      </div>

      {result && (
        <div className="mt-6 bg-slate-900 rounded-lg p-4">
          <div className="text-sm text-slate-400 mb-2">
            Detected language: {result.language_name}
          </div>

          <h3 className="text-white font-semibold">Summary</h3>
          <p className="text-slate-200 mt-1 whitespace-pre-wrap">{result.summary}</p>

          <div className="mt-3 flex items-center gap-2 flex-wrap">
            {voices.length > 0 && (
              <select
                value={voiceIndex ?? ""}
                onChange={(e) => setVoiceIndex(e.target.value === "" ? null : Number(e.target.value))}
                className="bg-slate-700 text-white text-sm rounded-lg px-2 py-1"
              >
                <option value="">Default voice for {result.language_name}</option>
                {voices.map((v, i) => (
                  <option key={i} value={i}>
                    {v.name} ({v.lang})
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={speakSummary}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-1.5 rounded-lg text-white text-sm"
            >
              🔊 Read Aloud
            </button>

            {saved ? (
              <span className="text-green-400 text-sm">✓ Saved as a searchable document</span>
            ) : (
              <button
                onClick={saveAsDocument}
                disabled={saving}
                className="bg-green-600 hover:bg-green-700 px-4 py-1.5 rounded-lg text-white text-sm disabled:opacity-50"
                title="Persist this scan into your document library so you can Chat/Study/Mind-Map it"
              >
                {saving ? "Saving..." : "💾 Save as Document"}
              </button>
            )}
          </div>

          <details className="mt-4">
            <summary className="text-slate-400 text-sm cursor-pointer">Full extracted text</summary>
            <p className="text-slate-300 text-sm mt-2 whitespace-pre-wrap">{result.extracted_text}</p>
          </details>
        </div>
      )}
    </div>
  );
}
