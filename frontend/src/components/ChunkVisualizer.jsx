import { useState } from "react";

export default function ChunkVisualizer({ chunks = [], isLoading = false }) {
  const [selectedChunk, setSelectedChunk] = useState(null);
  const [filter, setFilter] = useState("all");
  const [sortBy, setSortBy] = useState("similarity");

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-slate-700 rounded w-1/4"></div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  const filteredChunks = chunks
    .filter((chunk) => {
      if (filter === "all") return true;
      if (filter === "high" && chunk.similarity >= 0.8) return true;
      if (filter === "medium" && chunk.similarity >= 0.5 && chunk.similarity < 0.8) return true;
      if (filter === "low" && chunk.similarity < 0.5) return true;
      return false;
    })
    .sort((a, b) => {
      if (sortBy === "similarity") return b.similarity - a.similarity;
      if (sortBy === "page") return (a.page || 0) - (b.page || 0);
      if (sortBy === "confidence") return (b.confidence || 0) - (a.confidence || 0);
      return 0;
    });

  const stats = {
    total: chunks.length,
    high: chunks.filter((c) => c.similarity >= 0.8).length,
    medium: chunks.filter((c) => c.similarity >= 0.5 && c.similarity < 0.8).length,
    low: chunks.filter((c) => c.similarity < 0.5).length,
    avgSimilarity: chunks.length > 0
      ? (chunks.reduce((sum, c) => sum + (c.similarity || 0), 0) / chunks.length).toFixed(2)
      : 0,
  };

  return (
    <div className="bg-slate-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-white">Retrieved Chunks</h3>
          <span className="text-xs text-slate-400">{stats.total} chunks</span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-5 gap-2 mb-3">
          <div className="bg-slate-700/50 rounded-lg p-2 text-center">
            <p className="text-lg font-bold text-white">{stats.total}</p>
            <p className="text-xs text-slate-400">Total</p>
          </div>
          <div className="bg-green-900/30 rounded-lg p-2 text-center">
            <p className="text-lg font-bold text-green-400">{stats.high}</p>
            <p className="text-xs text-slate-400">High</p>
          </div>
          <div className="bg-amber-900/30 rounded-lg p-2 text-center">
            <p className="text-lg font-bold text-amber-400">{stats.medium}</p>
            <p className="text-xs text-slate-400">Medium</p>
          </div>
          <div className="bg-red-900/30 rounded-lg p-2 text-center">
            <p className="text-lg font-bold text-red-400">{stats.low}</p>
            <p className="text-xs text-slate-400">Low</p>
          </div>
          <div className="bg-blue-900/30 rounded-lg p-2 text-center">
            <p className="text-lg font-bold text-blue-400">{stats.avgSimilarity}</p>
            <p className="text-xs text-slate-400">Avg Score</p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Chunks</option>
            <option value="high">High Relevance (≥80%)</option>
            <option value="medium">Medium Relevance (50-80%)</option>
            <option value="low">Low Relevance (&lt;50%)</option>
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="similarity">Sort by Similarity</option>
            <option value="page">Sort by Page</option>
            <option value="confidence">Sort by Confidence</option>
          </select>
        </div>
      </div>

      {/* Chunks list */}
      <div className="p-4 max-h-96 overflow-y-auto space-y-3">
        {filteredChunks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <span className="text-4xl mb-2">📄</span>
            <p>No chunks retrieved</p>
          </div>
        ) : (
          filteredChunks.map((chunk, index) => (
            <ChunkCard
              key={chunk.id || index}
              chunk={chunk}
              index={index}
              isSelected={selectedChunk?.id === chunk.id}
              onClick={() => setSelectedChunk(selectedChunk?.id === chunk.id ? null : chunk)}
            />
          ))
        )}
      </div>

      {/* Chunk detail */}
      {selectedChunk && (
        <div className="p-4 border-t border-slate-700 bg-slate-900/50">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h4 className="font-medium text-white">
                {selectedChunk.title || `Chunk ${selectedChunk.id}`}
              </h4>
              {selectedChunk.section && (
                <p className="text-xs text-slate-400 mt-0.5">
                  Section: {selectedChunk.section}
                </p>
              )}
            </div>
            <button
              onClick={() => setSelectedChunk(null)}
              className="text-slate-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
            {selectedChunk.page && (
              <div className="bg-slate-700/50 rounded p-2">
                <p className="text-xs text-slate-400">Page</p>
                <p className="text-sm font-medium">{selectedChunk.page}</p>
              </div>
            )}
            <div className="bg-slate-700/50 rounded p-2">
              <p className="text-xs text-slate-400">Similarity</p>
              <p className="text-sm font-medium text-blue-400">
                {(selectedChunk.similarity * 100).toFixed(1)}%
              </p>
            </div>
            <div className="bg-slate-700/50 rounded p-2">
              <p className="text-xs text-slate-400">Confidence</p>
              <p className="text-sm font-medium text-green-400">
                {((selectedChunk.confidence || 0.9) * 100).toFixed(0)}%
              </p>
            </div>
            <div className="bg-slate-700/50 rounded p-2">
              <p className="text-xs text-slate-400">Tokens</p>
              <p className="text-sm font-medium">{selectedChunk.tokens || "N/A"}</p>
            </div>
          </div>

          {/* Entities */}
          {selectedChunk.entities && selectedChunk.entities.length > 0 && (
            <div className="mb-4">
              <p className="text-xs text-slate-400 mb-2">Entities</p>
              <div className="flex flex-wrap gap-1">
                {selectedChunk.entities.map((entity, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-purple-900/50 text-purple-300 rounded text-xs"
                  >
                    {entity}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Preview */}
          <div className="bg-slate-700/50 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-2">Preview</p>
            <p className="text-sm text-slate-300 line-clamp-3">
              {selectedChunk.preview || selectedChunk.content?.substring(0, 300)}
            </p>
          </div>

          {/* Reason */}
          {selectedChunk.reason && (
            <div className="mt-3 p-3 bg-blue-900/30 border border-blue-800 rounded-lg">
              <p className="text-xs text-blue-400 mb-1">Why Retrieved</p>
              <p className="text-sm text-slate-300">{selectedChunk.reason}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ChunkCard({ chunk, index, isSelected, onClick }) {
  const getSimilarityColor = (similarity) => {
    if (similarity >= 0.8) return "text-green-400 bg-green-500/20";
    if (similarity >= 0.5) return "text-amber-400 bg-amber-500/20";
    return "text-red-400 bg-red-500/20";
  };

  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-xl border cursor-pointer transition-all ${
        isSelected
          ? "bg-blue-900/20 border-blue-500"
          : "bg-slate-700/50 border-slate-700 hover:border-slate-600"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-6 h-6 bg-slate-600 rounded-full flex items-center justify-center text-xs font-medium">
              {index + 1}
            </span>
            <h4 className="font-medium text-white truncate">
              {chunk.title || `Chunk ${chunk.id || index + 1}`}
            </h4>
          </div>

          <p className="text-sm text-slate-400 line-clamp-2 mb-3">
            {chunk.preview || chunk.content?.substring(0, 150)}...
          </p>

          <div className="flex items-center gap-3 flex-wrap">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSimilarityColor(chunk.similarity)}`}>
              {(chunk.similarity * 100).toFixed(1)}% similar
            </span>
            {chunk.page && (
              <span className="text-xs text-slate-500">
                Page {chunk.page}
              </span>
            )}
            {chunk.section && (
              <span className="text-xs text-slate-500">
                {chunk.section}
              </span>
            )}
            {chunk.confidence && (
              <span className="text-xs text-slate-500">
                {((chunk.confidence || 0.9) * 100).toFixed(0)}% confidence
              </span>
            )}
          </div>

          {chunk.entities && chunk.entities.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {chunk.entities.slice(0, 3).map((entity, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 bg-purple-900/30 text-purple-300 rounded text-xs"
                >
                  {entity}
                </span>
              ))}
              {chunk.entities.length > 3 && (
                <span className="px-1.5 py-0.5 text-slate-500 text-xs">
                  +{chunk.entities.length - 3} more
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex-shrink-0">
          <div className="w-12 h-12 rounded-lg bg-slate-700 flex items-center justify-center">
            <span className="text-lg font-bold text-slate-400">
              {(chunk.similarity * 100).toFixed(0)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
