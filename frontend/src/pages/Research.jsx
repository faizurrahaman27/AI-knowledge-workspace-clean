import { useState, useEffect } from "react";
import api from "../api/axios";
import { getResearchAgents, createResearchReport, listReports, exportReport } from "../api/research";

const AGENT_TYPES = [
  { id: "literature_review", name: "Literature Review", description: "Synthesize findings from multiple sources" },
  { id: "source_synthesis", name: "Source Synthesis", description: "Combine and compare research sources" },
  { id: "academic_writing", name: "Academic Writing", description: "Generate structured academic content" },
  { id: "citation_analysis", name: "Citation Analysis", description: "Analyze and verify citations" },
  { id: "methodology_design", name: "Methodology Design", description: "Design research methodology" },
];

export default function Research() {
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState([]);
  const [reports, setReports] = useState([]);
  const [activeTab, setActiveTab] = useState("agents");
  const [query, setQuery] = useState("");
  const [sources, setSources] = useState("");
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAgents();
    fetchReports();
  }, []);

  const fetchAgents = async () => {
    try {
      const res = await getResearchAgents();
      setAgents(res.data);
    } catch (err) {
      console.log("Using default agents");
      setAgents(AGENT_TYPES);
    }
  };

  const fetchReports = async () => {
    try {
      const res = await listReports();
      setReports(res.data);
    } catch (err) {
      setReports([]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await createResearchReport({
        query,
        source_ids: sources.split(",").map(s => s.trim()).filter(Boolean),
        agent_type: selectedAgent,
      });
      setResult(res.data);
    } catch (err) {
      console.error("Research failed:", err);
      setError("Failed to process research request. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (reportId, format = "markdown") => {
    try {
      const res = await exportReport(reportId, format);
      const blob = new Blob([res.data], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `research_report.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold">Research Operating System</h1>
          <p className="text-slate-400 mt-1">Literature review, source synthesis, and academic research tools</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-slate-700 pb-2">
          {[
            { key: "agents", label: "Research Agents", icon: "🤖" },
            { key: "compose", label: "Compose Research", icon: "✍️" },
            { key: "reports", label: "My Reports", icon: "📊" },
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

        {/* Agents Tab */}
        {activeTab === "agents" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(agents.length > 0 ? agents : AGENT_TYPES).map((agent) => (
              <div
                key={agent.id}
                className="bg-slate-800 rounded-xl p-6 hover:bg-slate-700 transition cursor-pointer"
                onClick={() => {
                  setSelectedAgent(agent.id);
                  setActiveTab("compose");
                }}
              >
                <div className="text-3xl mb-3">
                  {agent.id === "literature_review" && "📚"}
                  {agent.id === "source_synthesis" && "🔄"}
                  {agent.id === "academic_writing" && "✍️"}
                  {agent.id === "citation_analysis" && "📖"}
                  {agent.id === "methodology_design" && "📐"}
                </div>
                <h3 className="text-lg font-semibold">{agent.name}</h3>
                <p className="text-slate-400 text-sm mt-2">{agent.description}</p>
                <div className="mt-4 flex gap-2">
                  <button className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm">
                    Use Agent
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Compose Tab */}
        {activeTab === "compose" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Input Form */}
            <div className="lg:col-span-2">
              <div className="bg-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-4">New Research</h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Research Query
                    </label>
                    <textarea
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="What would you like to research? (e.g., 'Compare transformer architectures for NLP tasks')"
                      className="w-full bg-slate-700 border border-slate-600 rounded-lg p-4 text-white placeholder-slate-400 h-32 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Source Documents (optional)
                    </label>
                    <input
                      type="text"
                      value={sources}
                      onChange={(e) => setSources(e.target.value)}
                      placeholder="Comma-separated document IDs"
                      className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Research Agent
                    </label>
                    <select
                      value={selectedAgent || ""}
                      onChange={(e) => setSelectedAgent(e.target.value || null)}
                      className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Select an agent (optional)</option>
                      {(agents.length > 0 ? agents : AGENT_TYPES).map((agent) => (
                        <option key={agent.id} value={agent.id}>{agent.name}</option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="submit"
                    disabled={loading || !query.trim()}
                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-medium transition"
                  >
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Processing...
                      </span>
                    ) : (
                      "Start Research"
                    )}
                  </button>
                </form>
                {error && (
                  <div className="mt-4 p-4 bg-red-900/50 border border-red-700 rounded-lg text-red-400">
                    {error}
                  </div>
                )}
              </div>
            </div>

            {/* Result Preview */}
            <div className="lg:col-span-1">
              <div className="bg-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-4">Preview</h3>
                {result ? (
                  <div className="space-y-4">
                    <div className="p-4 bg-slate-700 rounded-lg">
                      <p className="text-sm text-slate-400">Status</p>
                      <p className="font-medium">{result.status || "Completed"}</p>
                    </div>
                    {result.title && (
                      <div className="p-4 bg-slate-700 rounded-lg">
                        <p className="text-sm text-slate-400">Title</p>
                        <p className="font-medium">{result.title}</p>
                      </div>
                    )}
                    {result.summary && (
                      <div className="p-4 bg-slate-700 rounded-lg">
                        <p className="text-sm text-slate-400">Summary</p>
                        <p className="text-sm mt-1">{result.summary}</p>
                      </div>
                    )}
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleExport(result.id, "markdown")}
                        className="flex-1 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm"
                      >
                        Export MD
                      </button>
                      <button
                        onClick={() => handleExport(result.id, "pdf")}
                        className="flex-1 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm"
                      >
                        Export PDF
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-500">
                    <p>Your research results will appear here</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Reports Tab */}
        {activeTab === "reports" && (
          <div className="space-y-4">
            {reports.length > 0 ? (
              reports.map((report) => (
                <div key={report.id} className="bg-slate-800 rounded-xl p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-semibold">{report.title || "Research Report"}</h3>
                      <p className="text-sm text-slate-400 mt-1">
                        Created: {new Date(report.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleExport(report.id, "markdown")}
                        className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
                      >
                        Export
                      </button>
                    </div>
                  </div>
                  {report.summary && (
                    <p className="text-slate-300">{report.summary}</p>
                  )}
                </div>
              ))
            ) : (
              <div className="bg-slate-800 rounded-xl p-12 text-center">
                <p className="text-slate-400 mb-4">No research reports yet</p>
                <button
                  onClick={() => setActiveTab("compose")}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg"
                >
                  Create Your First Report
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
