import { useState } from "react";
import api from "../api/axios";

function TreeNode({ node, depth = 0 }) {
  const [collapsed, setCollapsed] = useState(false);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className={depth > 0 ? "ml-5 border-l border-slate-700 pl-4" : ""}>
      <div
        className={`flex items-center gap-2 py-1 ${hasChildren ? "cursor-pointer" : ""}`}
        onClick={() => hasChildren && setCollapsed((c) => !c)}
      >
        {hasChildren && <span className="text-slate-500 text-xs">{collapsed ? "▶" : "▼"}</span>}
        <span className={depth === 0 ? "text-white font-semibold" : "text-slate-200 text-sm"} dir="auto">
          {node.label || node.title || node.name}
        </span>
        {node.sources && node.sources.length > 0 && (
          <span className="flex gap-1 flex-wrap">
            {node.sources.map((s, i) => (
              <span key={i} className="text-[10px] bg-blue-900/60 text-blue-300 px-1.5 py-0.5 rounded-full">
                {s}
              </span>
            ))}
          </span>
        )}
      </div>

      {!collapsed && hasChildren && (
        <div>
          {node.children.map((child, i) => (
            <TreeNode key={i} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function MindMapPanel({ selectedDocument, workspace }) {
  const [tree, setTree] = useState(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    if (!selectedDocument && !workspace) {
      alert("Select a document or a workspace first.");
      return;
    }
    setLoading(true);
    setTree(null);
    try {
      const response = workspace
        ? await api.post("/mindmap/workspace", { workspace_id: workspace.id })
        : await api.post("/mindmap/", { document_id: selectedDocument.id });
      setTree(response.data);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Mind map generation failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-xl font-semibold text-white mb-1">
        {workspace ? `Knowledge Graph — ${workspace.name}` : "Mind Map"}
      </h2>
      <p className="text-slate-400 text-sm mb-4">
        {workspace
          ? "Merges concepts across every document in this workspace into one graph — the same idea appearing in two sources becomes one node citing both, instead of two separate trees. Click a branch to collapse/expand it."
          : "Generates a topic tree from the document. Click a branch to collapse/expand it. Switch to a workspace (Chat tab's scope selector) to merge concepts across multiple documents instead."}
      </p>

      <button
        onClick={generate}
        disabled={loading}
        className="bg-green-600 hover:bg-green-700 px-6 py-2 rounded-lg text-white disabled:opacity-50"
      >
        {loading ? "Generating..." : workspace ? "Generate Knowledge Graph" : "Generate Mind Map"}
      </button>

      {tree && (
        <div className="mt-6 bg-slate-900 rounded-lg p-4">
          <TreeNode node={tree} />
        </div>
      )}
    </div>
  );
}
