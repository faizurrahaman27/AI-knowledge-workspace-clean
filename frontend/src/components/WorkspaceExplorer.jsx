"""
WorkspaceExplorer Component

React component for managing workspaces, displaying workspace contents,
and navigating between workspaces.
"""

import { useState, useEffect } from "react";
import {
  createWorkspace,
  updateWorkspace,
  deleteWorkspace,
  archiveWorkspace,
  restoreWorkspace,
  toggleFavoriteWorkspace,
  listWorkspaces,
  listWorkspaceDocuments,
  addTagToWorkspace,
  removeTagFromWorkspace,
  uploadFile,
  importFromURL,
} from "../api/workspace";

export default function WorkspaceExplorer({
  currentWorkspace,
  onSelectWorkspace,
  onSelectDocument,
  onUploadComplete,
}) {
  const [workspaces, setWorkspaces] = useState([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [workspaceDocuments, setWorkspaceDocuments] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState("all"); // all, active, archived, favorites
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [newWorkspaceDescription, setNewWorkspaceDescription] = useState("");
  const [importURL, setImportURL] = useState("");
  const [importType, setImportType] = useState("web_page");
  const [isLoading, setIsLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  // Fetch workspaces
  const fetchWorkspaces = async () => {
    try {
      const params = {};
      if (filter === "favorites") params.favorites = true;
      else if (filter !== "all") params.status = filter;
      
      const data = await listWorkspaces(params);
      setWorkspaces(data);
    } catch (err) {
      console.error("Failed to fetch workspaces:", err);
    }
  };

  // Fetch workspace documents when workspace changes
  useEffect(() => {
    if (currentWorkspace) {
      fetchWorkspaceDocuments(currentWorkspace.id);
    } else {
      setWorkspaceDocuments([]);
    }
  }, [currentWorkspace]);

  const fetchWorkspaceDocuments = async (workspaceId) => {
    try {
      const docs = await listWorkspaceDocuments(workspaceId);
      setWorkspaceDocuments(docs);
    } catch (err) {
      console.error("Failed to fetch workspace documents:", err);
    }
  };

  // Create workspace
  const handleCreateWorkspace = async (e) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;

    try {
      setIsLoading(true);
      await createWorkspace({
        name: newWorkspaceName.trim(),
        description: newWorkspaceDescription.trim() || undefined,
      });
      setNewWorkspaceName("");
      setNewWorkspaceDescription("");
      setShowCreateDialog(false);
      fetchWorkspaces();
    } catch (err) {
      console.error("Failed to create workspace:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Archive workspace
  const handleArchive = async (workspace) => {
    try {
      if (workspace.status === "archived") {
        await restoreWorkspace(workspace.id);
      } else {
        await archiveWorkspace(workspace.id);
      }
      fetchWorkspaces();
    } catch (err) {
      console.error("Failed to archive/restore workspace:", err);
    }
  };

  // Delete workspace
  const handleDelete = async (workspace) => {
    if (!confirm(`Delete workspace "${workspace.name}"?`)) return;
    
    try {
      await deleteWorkspace(workspace.id);
      if (currentWorkspace?.id === workspace.id) {
        onSelectWorkspace(null);
      }
      fetchWorkspaces();
    } catch (err) {
      console.error("Failed to delete workspace:", err);
    }
  };

  // Toggle favorite
  const handleToggleFavorite = async (workspace) => {
    try {
      await toggleFavoriteWorkspace(workspace.id);
      fetchWorkspaces();
    } catch (err) {
      console.error("Failed to toggle favorite:", err);
    }
  };

  // Handle file upload
  const handleFileUpload = async (files) => {
    if (!currentWorkspace || !files.length) return;

    try {
      setIsLoading(true);
      for (const file of files) {
        await uploadFile(file, currentWorkspace.id);
      }
      setShowUploadDialog(false);
      fetchWorkspaceDocuments(currentWorkspace.id);
      if (onUploadComplete) onUploadComplete();
    } catch (err) {
      console.error("Failed to upload files:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle drag and drop
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (!currentWorkspace) return;

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await handleFileUpload(files);
    }
  };

  // Handle URL import
  const handleImport = async (e) => {
    e.preventDefault();
    if (!importURL.trim() || !currentWorkspace) return;

    try {
      setIsLoading(true);
      await importFromURL(importURL.trim(), importType, currentWorkspace.id);
      setImportURL("");
      setShowImportDialog(false);
      fetchWorkspaceDocuments(currentWorkspace.id);
    } catch (err) {
      console.error("Failed to import URL:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter documents
  const filteredDocuments = workspaceDocuments.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Get status badge color
  const getStatusBadge = (workspace) => {
    if (workspace.status === "archived") {
      return "bg-yellow-600/20 text-yellow-400";
    }
    if (workspace.is_favorite) {
      return "bg-orange-600/20 text-orange-400";
    }
    return "bg-green-600/20 text-green-400";
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Workspaces</h2>
          <button
            onClick={() => setShowCreateDialog(true)}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white"
            title="Create workspace"
          >
            +
          </button>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 mb-3">
          {["all", "active", "archived", "favorites"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-1 text-xs rounded ${
                filter === f
                  ? "bg-slate-700 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Workspace list */}
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {workspaces.map((ws) => (
            <div
              key={ws.id}
              onClick={() => onSelectWorkspace(ws)}
              className={`p-2 rounded-lg cursor-pointer group ${
                currentWorkspace?.id === ws.id
                  ? "bg-blue-600/30 border border-blue-500"
                  : "hover:bg-slate-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-lg">{ws.icon || "📁"}</span>
                  <span className="truncate text-sm">{ws.name}</span>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleToggleFavorite(ws);
                    }}
                    className="p-1 hover:bg-slate-600 rounded"
                    title={ws.is_favorite ? "Remove from favorites" : "Add to favorites"}
                  >
                    {ws.is_favorite ? "★" : "☆"}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleArchive(ws);
                    }}
                    className="p-1 hover:bg-slate-600 rounded"
                    title={ws.status === "archived" ? "Restore" : "Archive"}
                  >
                    {ws.status === "archived" ? "↩" : "📦"}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(ws);
                    }}
                    className="p-1 hover:bg-red-600 rounded"
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
                <span className={getStatusBadge(ws)}>
                  {ws.status === "archived" ? "Archived" : ws.is_favorite ? "★" : ""}
                </span>
                <span>{ws.source_count || 0} sources</span>
              </div>
            </div>
          ))}
          {workspaces.length === 0 && (
            <p className="text-slate-500 text-sm text-center py-4">
              No workspaces found
            </p>
          )}
        </div>
      </div>

      {/* Current workspace content */}
      {currentWorkspace && (
        <div className="flex-1 flex flex-col min-h-0">
          <div className="p-4 border-b border-slate-700">
            <h3 className="font-medium text-white truncate">
              {currentWorkspace.icon || "📁"} {currentWorkspace.name}
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              {workspaceDocuments.length} sources
            </p>

            {/* Action buttons */}
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => setShowUploadDialog(true)}
                className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm"
              >
                📤 Upload
              </button>
              <button
                onClick={() => setShowImportDialog(true)}
                className="flex-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm"
              >
                🔗 Import URL
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="p-3 border-b border-slate-700">
            <input
              type="text"
              placeholder="Search sources..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded text-sm text-white placeholder-slate-400"
            />
          </div>

          {/* Document list */}
          <div className="flex-1 overflow-y-auto p-2">
            {filteredDocuments.map((doc) => (
              <div
                key={doc.id}
                onClick={() => onSelectDocument(doc)}
                className="p-2 rounded hover:bg-slate-700 cursor-pointer mb-1"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm">📄</span>
                  <span className="text-sm truncate">{doc.filename}</span>
                </div>
                <div className="text-xs text-slate-400 mt-1 pl-6">
                  {doc.language_name || "Unknown"} • {doc.content_type}
                </div>
              </div>
            ))}
            {filteredDocuments.length === 0 && (
              <p className="text-slate-500 text-sm text-center py-8">
                No sources yet. Upload files or import URLs.
              </p>
            )}
          </div>

          {/* Drop zone indicator */}
          {dragActive && (
            <div
              className="absolute inset-0 bg-blue-600/20 border-2 border-dashed border-blue-500 rounded-lg flex items-center justify-center"
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <span className="text-blue-400 font-medium">Drop files to upload</span>
            </div>
          )}
        </div>
      )}

      {/* Create workspace dialog */}
      {showCreateDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Create Workspace</h3>
            <form onSubmit={handleCreateWorkspace}>
              <input
                type="text"
                placeholder="Workspace name"
                value={newWorkspaceName}
                onChange={(e) => setNewWorkspaceName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white mb-3"
                autoFocus
              />
              <textarea
                placeholder="Description (optional)"
                value={newWorkspaceDescription}
                onChange={(e) => setNewWorkspaceDescription(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white mb-4"
                rows={3}
              />
              <div className="flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowCreateDialog(false)}
                  className="px-4 py-2 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newWorkspaceName.trim() || isLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white disabled:opacity-50"
                >
                  {isLoading ? "Creating..." : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Upload dialog */}
      {showUploadDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Upload Files</h3>
            <div
              className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center mb-4"
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={(e) => {
                handleDrop(e);
                setShowUploadDialog(false);
              }}
            >
              <input
                type="file"
                multiple
                onChange={(e) => {
                  handleFileUpload(Array.from(e.target.files));
                  setShowUploadDialog(false);
                }}
                className="hidden"
                id="file-upload"
                accept=".pdf,.txt,.md,.csv,.json,.docx,.pptx,.jpg,.jpeg,.png,.gif,.webp"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <div className="text-4xl mb-2">📤</div>
                <p className="text-slate-300">Click to select files</p>
                <p className="text-xs text-slate-500 mt-2">
                  PDF, TXT, MD, CSV, JSON, DOCX, PPTX, Images, ZIP
                </p>
              </label>
            </div>
            <button
              onClick={() => setShowUploadDialog(false)}
              className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-white"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Import URL dialog */}
      {showImportDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Import from URL</h3>
            <form onSubmit={handleImport}>
              <select
                value={importType}
                onChange={(e) => setImportType(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white mb-3"
              >
                <option value="web_page">Web Page</option>
                <option value="github_file">GitHub File</option>
                <option value="research_paper">Research Paper</option>
              </select>
              <input
                type="url"
                placeholder="Enter URL..."
                value={importURL}
                onChange={(e) => setImportURL(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white mb-4"
                autoFocus
              />
              <div className="flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowImportDialog(false)}
                  className="px-4 py-2 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!importURL.trim() || isLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white disabled:opacity-50"
                >
                  {isLoading ? "Importing..." : "Import"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
