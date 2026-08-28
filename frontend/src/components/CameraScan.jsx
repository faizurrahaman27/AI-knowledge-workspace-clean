import { useRef, useState } from "react";
import api from "../api/axios";

export default function CameraScan({ fetchDocuments }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [streaming, setStreaming] = useState(false);
  const [shots, setShots] = useState([]); // array of { blob, previewUrl }
  const [uploading, setUploading] = useState(false);
  const [docName, setDocName] = useState("Scanned Document.pdf");

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setStreaming(true);
    } catch (err) {
      console.error(err);
      alert("Could not access the camera. Check browser permissions.");
    }
  };

  const stopCamera = () => {
    const stream = videoRef.current?.srcObject;
    stream?.getTracks().forEach((t) => t.stop());
    setStreaming(false);
  };

  const capture = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
      if (!blob) return;
      setShots((prev) => [...prev, { blob, previewUrl: URL.createObjectURL(blob) }]);
    }, "image/jpeg", 0.92);
  };

  const removeShot = (index) => {
    setShots((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadShots = async () => {
    if (shots.length === 0) return;
    setUploading(true);

    const formData = new FormData();
    shots.forEach((s, i) => formData.append("files", s.blob, `page_${i + 1}.jpg`));
    formData.append("document_name", docName || "Scanned Document.pdf");

    try {
      await api.post("/documents/upload-from-scan", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setShots([]);
      stopCamera();
      fetchDocuments?.();
      alert("Scanned document created — you can now chat with it like any PDF.");
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-xl font-semibold text-white mb-1">Scan Document (Camera)</h2>
      <p className="text-slate-400 text-sm mb-4">
        Capture one photo per page — they'll be merged into a single PDF and processed
        exactly like an upload (chunked, embedded, searchable, chattable).
      </p>

      {!streaming ? (
        <button onClick={startCamera} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-white">
          📷 Open Camera
        </button>
      ) : (
        <div>
          <video ref={videoRef} className="w-full max-w-md rounded-lg border border-slate-700" muted playsInline />
          <div className="mt-3 flex gap-2">
            <button onClick={capture} className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-white">
              📸 Capture Page
            </button>
            <button onClick={stopCamera} className="bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded-lg text-white">
              Stop Camera
            </button>
          </div>
        </div>
      )}

      <canvas ref={canvasRef} className="hidden" />

      {shots.length > 0 && (
        <div className="mt-6">
          <div className="text-sm text-slate-300 mb-2">{shots.length} page(s) captured</div>
          <div className="flex flex-wrap gap-3">
            {shots.map((s, i) => (
              <div key={i} className="relative">
                <img src={s.previewUrl} alt={`page ${i + 1}`} className="h-28 rounded border border-slate-700" />
                <button
                  onClick={() => removeShot(i)}
                  className="absolute -top-2 -right-2 bg-red-600 rounded-full w-6 h-6 text-xs text-white"
                >
                  ✕
                </button>
                <div className="text-center text-xs text-slate-400 mt-1">Page {i + 1}</div>
              </div>
            ))}
          </div>

          <input
            value={docName}
            onChange={(e) => setDocName(e.target.value)}
            placeholder="Document name"
            className="mt-4 w-full max-w-sm bg-slate-700 text-white text-sm rounded-lg px-3 py-2 outline-none"
          />

          <button
            onClick={uploadShots}
            disabled={uploading}
            className="mt-3 bg-green-600 hover:bg-green-700 px-6 py-2 rounded-lg text-white disabled:opacity-50 block"
          >
            {uploading ? "Processing..." : `Create PDF from ${shots.length} page(s)`}
          </button>
        </div>
      )}

      <p className="text-slate-500 text-xs mt-4">
        Note: this captures and merges pages as-is (no automatic crop/deskew yet) — frame
        each page as squarely as you can for best OCR/text-extraction results.
      </p>
    </div>
  );
}
