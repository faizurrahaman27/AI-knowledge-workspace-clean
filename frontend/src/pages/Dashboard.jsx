import { useEffect, useState } from "react";
import api from "../api/axios";
import { listWorkspaces } from "../api/workspace";

import Navbar from "../components/Navbar";
import Sidebar from "../components/Sidebar";
import InstallPrompt from "../components/InstallPrompt";
import UploadPanel from "../components/UploadPanel";
import ChatPanel from "../components/ChatPanel";
import PdfViewer from "../components/PdfViewer";
import ScanPanel from "../components/ScanPanel";
import StudyPanel from "../components/StudyPanel";
import StudyPackPanel from "../components/StudyPackPanel";
import ComparePanel from "../components/ComparePanel";
import MindMapPanel from "../components/MindMapPanel";
import CameraScan from "../components/CameraScan";
import WorkspacesPanel from "../components/WorkspacesPanel";
import LiveActivity from "../components/LiveActivity";
import StreamingChat from "../components/StreamingChat";

const TABS = [
  { key: "chat", label: "Chat" },
  { key: "live", label: "Live Activity" },
  { key: "study", label: "Study Mode" },
  { key: "studypack", label: "AI Agent" },
  { key: "mindmap", label: "Mind Map / Knowledge Graph" },
  { key: "compare", label: "Compare" },
  { key: "scan", label: "Scan & Listen" },
  { key: "camera", label: "Camera Scan" },
  { key: "workspaces", label: "Workspaces & Teams" },
];

export default function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState(null);
  const [activeTab, setActiveTab] = useState("chat");
  const [jumpToPage, setJumpToPage] = useState(null);
  const [highlightSnippet, setHighlightSnippet] = useState(null);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [openTabs, setOpenTabs] = useState([]); // documents opened as tabs in the PDF viewer
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeView, setActiveView] = useState('document'); // 'document' or 'chat'
  const [chatView, setChatView] = useState("chat"); // "chat" | "document" — toggle instead of side-by-side

  const fetchDocuments = async () => {
    try {
      const response = await api.get("/documents/");
      setDocuments(response.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchWorkspaces = async () => {
    try {
      setWorkspaces(await listWorkspaces());
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchDocuments();
    fetchWorkspaces();
  }, []);

  // Selecting a document switches chat scope back to single-document mode,
  // and opens it as a tab in the PDF viewer if it isn't already (multi-PDF
  // tabs -- previously this state existed but nothing ever populated it).
  const handleSelectDocument = (doc) => {
    setSelectedWorkspace(null);
    setSelectedDocument(doc);
    setOpenTabs((prev) => (prev.some((d) => d.id === doc.id) ? prev : [...prev, doc]));
  };

  const closeTab = (docId, e) => {
    e.stopPropagation();
    setOpenTabs((prev) => {
      const next = prev.filter((d) => d.id !== docId);
      if (selectedDocument?.id === docId) {
        setSelectedDocument(next.length > 0 ? next[next.length - 1] : null);
      }
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col">
      <Navbar onMenuClick={() => setSidebarOpen(true)} />

      <div className="flex flex-1 min-h-0">
        <Sidebar
          documents={documents}
          selectedDocument={selectedDocument}
          setSelectedDocument={handleSelectDocument}
          fetchDocuments={fetchDocuments}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        <div className="flex-1 p-4 sm:p-6 lg:p-8 flex flex-col min-w-0 overflow-y-auto">
          <InstallPrompt />

          <p className="text-slate-400 text-sm sm:text-base">
            Upload, scan, or photograph documents — chat with citations, live pipeline
            progress, translations, comparisons, mind maps, and study tools. Group documents
            into a Workspace, share it with a Team, and chat about all of them together, live.
          </p>

          <div className="mt-6">
            <UploadPanel fetchDocuments={fetchDocuments} />
          </div>

          {selectedDocument?.language_name && (
            <div className="mt-3 text-sm text-slate-400">
              Detected document language: <strong>{selectedDocument.language_name}</strong>
            </div>
          )}

          {activeTab === "chat" && workspaces.length > 0 && (
            <div className="mt-4 flex items-center gap-2 flex-wrap">
              <span className="text-slate-400 text-sm">Chat scope:</span>
              <button
                onClick={() => setSelectedWorkspace(null)}
                className={`px-3 py-1 rounded-lg text-xs ${
                  !selectedWorkspace ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-300"
                }`}
              >
                Single document
              </button>
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => setSelectedWorkspace(ws)}
                  className={`px-3 py-1 rounded-lg text-xs ${
                    selectedWorkspace?.id === ws.id ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-300"
                  }`}
                >
                  {ws.name} {ws.team_id ? "👥" : ""}
                </button>
              ))}
            </div>
          )}

          <div className="mt-6 flex gap-2 border-b border-slate-700 flex-wrap overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium rounded-t-lg whitespace-nowrap ${
                  activeTab === tab.key
                    ? "bg-slate-800 text-white"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="mt-4 flex-1 min-h-0">
            {activeTab === "chat" && (
              <div className="h-auto lg:h-[70vh] flex flex-col min-h-0">
                {/* Toggle switch: replaces the old side-by-side split so
                    neither panel has to fight the other for space. Hidden
                    entirely in workspace mode since there's no single PDF
                    to preview there. */}
                {!selectedWorkspace && (
                  <div className="flex items-center justify-center py-2 shrink-0">
                    <div className="inline-flex bg-slate-800 rounded-full p-1 gap-1">
                      <button
                        onClick={() => setChatView("chat")}
                        className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-medium transition ${
                          chatView === "chat" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        💬 Chat
                      </button>
                      <button
                        onClick={() => setChatView("document")}
                        disabled={!selectedDocument}
                        className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-medium transition disabled:opacity-40 disabled:cursor-not-allowed ${
                          chatView === "document" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        📄 Document
                      </button>
                    </div>
                  </div>
                )}

                <div className="flex-1 min-h-0 relative">
                  {/* PDF viewer — full width, only visible in "document" view.
                      Stays mounted while hidden so scroll position, rendered
                      pages, and the notes panel don't reset when toggling. */}
                  {!selectedWorkspace && (
                    <div className={`absolute inset-0 flex flex-col min-h-0 ${chatView === "document" ? "flex" : "hidden"}`}>
                      {openTabs.length > 1 && (
                        <div className="flex gap-1 overflow-x-auto mb-1 shrink-0">
                          {openTabs.map((d) => (
                            <button
                              key={d.id}
                              onClick={() => setSelectedDocument(d)}
                              className={`flex items-center gap-2 px-3 py-1.5 rounded-t-lg text-xs whitespace-nowrap ${
                                selectedDocument?.id === d.id
                                  ? "bg-slate-800 text-white"
                                  : "bg-slate-900 text-slate-400 hover:text-white"
                              }`}
                              title={d.filename}
                            >
                              <span className="max-w-[10rem] truncate">{d.filename}</span>
                              <span
                                onClick={(e) => closeTab(d.id, e)}
                                className="hover:text-red-400"
                                role="button"
                                aria-label={`Close ${d.filename}`}
                              >
                                ✕
                              </span>
                            </button>
                          ))}
                        </div>
                      )}
                      <div className="flex-1 min-h-0">
                        <PdfViewer
                          document={selectedDocument}
                          jumpToPage={jumpToPage}
                          highlightSnippet={highlightSnippet}
                          onAskAboutSelection={(text) => {
                            setPendingQuestion(`Explain this: "${text}"`);
                            setChatView("chat");
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Chat — full width, only visible in "chat" view (or
                      always, in workspace mode where there's no PDF pane). */}
                  <div
                    className={`absolute inset-0 min-h-0 ${
                      selectedWorkspace || chatView === "chat" ? "block" : "hidden"
                    }`}
                  >
                    <ChatPanel
                      selectedDocument={selectedWorkspace ? null : selectedDocument}
                      workspace={selectedWorkspace}
                      prefillQuestion={pendingQuestion}
                      onPrefillConsumed={() => setPendingQuestion(null)}
                      onCitationClick={(page, snippet) => {
                        setJumpToPage(page);
                        setHighlightSnippet(snippet || null);
                        setChatView("document");
                      }}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === "live" && (
              <LiveActivity
                workspaceId={selectedWorkspace?.id}
                documentId={selectedDocument?.id}
              />
            )}

            {activeTab === "study" && <StudyPanel selectedDocument={selectedDocument} />}
            {activeTab === "studypack" && <StudyPackPanel selectedDocument={selectedDocument} />}
            {activeTab === "mindmap" && (
              <MindMapPanel selectedDocument={selectedDocument} workspace={selectedWorkspace} />
            )}
            {activeTab === "compare" && <ComparePanel documents={documents} />}
            {activeTab === "scan" && <ScanPanel fetchDocuments={fetchDocuments} />}
            {activeTab === "camera" && <CameraScan fetchDocuments={fetchDocuments} />}
            {activeTab === "workspaces" && (
              <WorkspacesPanel documents={documents} onWorkspacesChanged={setWorkspaces} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}