import { useState } from "react";

const MOCK_VIDEOS = [
  { id: 1, title: "Introduction to Neural Networks", duration: "15:30", status: "completed" },
  { id: 2, title: "Deep Learning Fundamentals", duration: "22:45", status: "completed" },
  { id: 3, title: "Transformers Architecture", duration: "18:20", status: "processing" },
];

export default function Video() {
  const [videos, setVideos] = useState(MOCK_VIDEOS);
  const [activeTab, setActiveTab] = useState("library");
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadFile(file);
      // Simulate upload
      const newVideo = {
        id: videos.length + 1,
        title: file.name.replace(/\.[^/.]+$/, ""),
        duration: "Processing...",
        status: "uploading",
      };
      setVideos([...videos, newVideo]);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold">Video Learning</h1>
          <p className="text-slate-400 mt-1">Video transcription, summarization, and transcript-based chat</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-slate-700 pb-2">
          {[
            { key: "library", label: "Video Library", icon: "📚" },
            { key: "upload", label: "Upload Video", icon: "⬆️" },
            { key: "transcripts", label: "Transcripts", icon: "📝" },
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

        {/* Video Library */}
        {activeTab === "library" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {videos.map((video) => (
              <div
                key={video.id}
                onClick={() => setSelectedVideo(video)}
                className={`bg-slate-800 rounded-xl overflow-hidden cursor-pointer transition ${
                  selectedVideo?.id === video.id ? "ring-2 ring-blue-500" : "hover:bg-slate-700"
                }`}
              >
                <div className="aspect-video bg-slate-700 flex items-center justify-center">
                  {video.status === "completed" ? (
                    <span className="text-4xl">▶️</span>
                  ) : video.status === "processing" ? (
                    <span className="text-2xl animate-pulse">⏳ Processing...</span>
                  ) : (
                    <span className="text-2xl animate-pulse">⬆️ Uploading...</span>
                  )}
                </div>
                <div className="p-4">
                  <h3 className="font-semibold truncate">{video.title}</h3>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-sm text-slate-400">{video.duration}</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      video.status === "completed" ? "bg-green-500/20 text-green-400" :
                      video.status === "processing" ? "bg-amber-500/20 text-amber-400" :
                      "bg-blue-500/20 text-blue-400"
                    }`}>
                      {video.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Upload */}
        {activeTab === "upload" && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Upload Video</h3>
            <div className="border-2 border-dashed border-slate-600 rounded-xl p-12 text-center mb-6">
              <input
                type="file"
                accept="video/*"
                onChange={handleFileUpload}
                className="hidden"
                id="video-upload"
              />
              <label htmlFor="video-upload" className="cursor-pointer">
                <p className="text-4xl mb-4">📹</p>
                <p className="text-slate-300">
                  {uploadFile ? uploadFile.name : "Click to upload or drag and drop"}
                </p>
                <p className="text-sm text-slate-500 mt-2">MP4, MOV, AVI up to 500MB</p>
              </label>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Video Title</label>
                <input
                  type="text"
                  placeholder="Enter video title"
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Description (optional)</label>
                <textarea
                  placeholder="Add a description..."
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium">
                Upload & Process
              </button>
            </div>
          </div>
        )}

        {/* Transcripts */}
        {activeTab === "transcripts" && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Video Transcripts</h3>
            {selectedVideo ? (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h4 className="font-medium">{selectedVideo.title}</h4>
                  <div className="flex gap-2">
                    <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">
                      Generate Summary
                    </button>
                    <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">
                      Create Flashcards
                    </button>
                  </div>
                </div>
                <div className="bg-slate-700 rounded-lg p-4 h-96 overflow-y-auto">
                  <p className="text-slate-300 leading-relaxed">
                    00:00 - Introduction to neural networks and their importance in machine learning...
                    <br /><br />
                    00:30 - What are neural networks? A brief overview of biological and artificial neurons...
                    <br /><br />
                    01:15 - The structure of a neural network: input, hidden, and output layers...
                    <br /><br />
                    02:00 - Understanding activation functions and their role...
                    <br /><br />
                    03:30 - Backpropagation: How neural networks learn from errors...
                    <br /><br />
                    05:00 - Practical example: Building a simple neural network in Python...
                  </p>
                </div>
                <div className="mt-4 flex gap-2">
                  <button className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm">
                    Generate Quiz
                  </button>
                  <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">
                    Export Transcript
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-slate-500 text-center py-12">
                Select a video to view its transcript
              </p>
            )}
          </div>
        )}

        {/* Selected Video Detail */}
        {selectedVideo && activeTab === "library" && (
          <div className="mt-6 bg-slate-800 rounded-xl p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-semibold">{selectedVideo.title}</h3>
                <p className="text-slate-400">Duration: {selectedVideo.duration}</p>
              </div>
              <button
                onClick={() => setSelectedVideo(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕ Close
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { icon: "📝", label: "Transcript" },
                { icon: "🧠", label: "Summary" },
                { icon: "🃏", label: "Flashcards" },
                { icon: "❓", label: "Quiz" },
              ].map((action) => (
                <button
                  key={action.label}
                  className="p-4 bg-slate-700 hover:bg-slate-600 rounded-lg text-center"
                >
                  <p className="text-2xl mb-2">{action.icon}</p>
                  <p className="text-sm">{action.label}</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
