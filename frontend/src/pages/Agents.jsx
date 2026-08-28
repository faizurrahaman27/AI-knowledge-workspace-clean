import { useState, useEffect } from "react";
import { getAgents, getTeams, executeAgent, executeTeam, getOrchestrationStatus } from "../api/multiAgent";

const AGENT_CATEGORIES = {
  research: { icon: "🔬", color: "blue" },
  analysis: { icon: "📊", color: "green" },
  writing: { icon: "✍️", color: "purple" },
  creative: { icon: "🎨", color: "pink" },
  automation: { icon: "⚡", color: "amber" },
};

const MOCK_AGENTS = [
  { id: "agent-1", name: "Research Agent", category: "research", description: "Deep research and analysis", capabilities: ["web_search", "source_verification", "citation"] },
  { id: "agent-2", name: "Data Analyst", category: "analysis", description: "Statistical analysis and insights", capabilities: ["charts", "predictions", "reports"] },
  { id: "agent-3", name: "Writer Agent", category: "writing", description: "Content creation and editing", capabilities: ["drafts", "editing", "formatting"] },
  { id: "agent-4", name: "Creative Agent", category: "creative", description: "Creative brainstorming and ideation", capabilities: ["ideas", "concepts", "brainstorming"] },
  { id: "agent-5", name: "Automation Agent", category: "automation", description: "Workflow automation", capabilities: ["scheduling", "notifications", "integration"] },
];

export default function Agents() {
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState([]);
  const [teams, setTeams] = useState([]);
  const [orchestrationStatus, setOrchestrationStatus] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [taskInput, setTaskInput] = useState("");
  const [activeTab, setActiveTab] = useState("agents");
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [agentsRes, teamsRes, statusRes] = await Promise.allSettled([
        getAgents(),
        getTeams(),
        getOrchestrationStatus(),
      ]);

      if (agentsRes.status === "fulfilled") setAgents(agentsRes.value.data);
      if (teamsRes.status === "fulfilled") setTeams(teamsRes.value.data);
      if (statusRes.status === "fulfilled") setOrchestrationStatus(statusRes.value.data);
    } catch (err) {
      console.log("Using demo data");
    } finally {
      setLoading(false);
      if (agents.length === 0) setAgents(MOCK_AGENTS);
    }
  };

  const handleExecuteAgent = async (agentId) => {
    if (!taskInput.trim()) return;
    setExecuting(true);
    setError(null);
    try {
      const res = await executeAgent(agentId, { task: taskInput });
      setResult(res.data);
    } catch (err) {
      setError("Failed to execute agent. Please try again.");
    } finally {
      setExecuting(false);
    }
  };

  const handleExecuteTeam = async (teamId) => {
    if (!taskInput.trim()) return;
    setExecuting(true);
    setError(null);
    try {
      const res = await executeTeam(teamId, { task: taskInput });
      setResult(res.data);
    } catch (err) {
      setError("Failed to execute team. Please try again.");
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold">Agent Studio</h1>
          <p className="text-slate-400 mt-1">Custom AI workflows and agent orchestration</p>
        </div>

        {/* System Status */}
        {orchestrationStatus && (
          <div className="bg-slate-800 rounded-xl p-4 mb-6 flex flex-wrap gap-6">
            <div>
              <p className="text-sm text-slate-400">Active Agents</p>
              <p className="text-xl font-bold">{orchestrationStatus.active_agents || agents.length}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">Tasks Completed</p>
              <p className="text-xl font-bold">{orchestrationStatus.tasks_completed || 0}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">System Status</p>
              <p className="text-xl font-bold text-green-400">Online</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-slate-700 pb-2">
          {[
            { key: "agents", label: "Agents", icon: "🤖" },
            { key: "teams", label: "Teams", icon: "👥" },
            { key: "workspace", label: "Workspace", icon: "⚡" },
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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Agent Grid */}
            <div className="lg:col-span-2">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {(agents.length > 0 ? agents : MOCK_AGENTS).map((agent) => {
                  const category = AGENT_CATEGORIES[agent.category] || AGENT_CATEGORIES.automation;
                  return (
                    <div
                      key={agent.id}
                      onClick={() => setSelectedAgent(agent)}
                      className={`bg-slate-800 rounded-xl p-5 cursor-pointer transition ${
                        selectedAgent?.id === agent.id ? "ring-2 ring-blue-500" : "hover:bg-slate-700"
                      }`}
                    >
                      <div className="flex items-center gap-3 mb-3">
                        <span className="text-2xl">{category.icon}</span>
                        <div>
                          <h3 className="font-semibold">{agent.name}</h3>
                          <p className="text-xs text-slate-400">{agent.category}</p>
                        </div>
                      </div>
                      <p className="text-sm text-slate-400 mb-4">{agent.description}</p>
                      {agent.capabilities && (
                        <div className="flex flex-wrap gap-1">
                          {agent.capabilities.slice(0, 3).map((cap) => (
                            <span key={cap} className="px-2 py-0.5 bg-slate-700 rounded text-xs">
                              {cap}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Agent Detail Panel */}
            <div className="lg:col-span-1">
              <div className="bg-slate-800 rounded-xl p-6 sticky top-4">
                <h3 className="text-lg font-semibold mb-4">
                  {selectedAgent ? selectedAgent.name : "Select an Agent"}
                </h3>
                {selectedAgent ? (
                  <>
                    <p className="text-slate-400 mb-4">{selectedAgent.description}</p>
                    
                    <div className="mb-4">
                      <p className="text-sm font-medium mb-2">Capabilities</p>
                      <div className="flex flex-wrap gap-1">
                        {(selectedAgent.capabilities || []).map((cap) => (
                          <span key={cap} className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="mb-4">
                      <label className="block text-sm font-medium mb-2">Task</label>
                      <textarea
                        value={taskInput}
                        onChange={(e) => setTaskInput(e.target.value)}
                        placeholder="Enter your task..."
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-400 h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <button
                      onClick={() => handleExecuteAgent(selectedAgent.id)}
                      disabled={executing || !taskInput.trim()}
                      className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-medium transition"
                    >
                      {executing ? "Executing..." : "Execute Agent"}
                    </button>
                  </>
                ) : (
                  <p className="text-slate-500 text-center py-8">
                    Click an agent to select it
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Teams Tab */}
        {activeTab === "teams" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              {teams.length > 0 ? (
                <div className="space-y-4">
                  {teams.map((team) => (
                    <div key={team.id} className="bg-slate-800 rounded-xl p-6">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-lg font-semibold">{team.name}</h3>
                          <p className="text-sm text-slate-400">{team.description}</p>
                        </div>
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">
                          {team.agent_count || 0} agents
                        </span>
                      </div>
                      <button
                        onClick={() => setSelectedTeam(team)}
                        className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
                      >
                        Manage Team
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-slate-800 rounded-xl p-12 text-center">
                  <p className="text-slate-400 mb-4">No teams configured</p>
                  <button className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg">
                    Create Team
                  </button>
                </div>
              )}
            </div>
            <div className="lg:col-span-1">
              <div className="bg-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-4">Team Workspace</h3>
                {selectedTeam ? (
                  <>
                    <p className="text-slate-400 mb-4">{selectedTeam.name}</p>
                    <div className="mb-4">
                      <label className="block text-sm font-medium mb-2">Team Task</label>
                      <textarea
                        value={taskInput}
                        onChange={(e) => setTaskInput(e.target.value)}
                        placeholder="Describe the task for the team..."
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-400 h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <button
                      onClick={() => handleExecuteTeam(selectedTeam.id)}
                      disabled={executing || !taskInput.trim()}
                      className="w-full py-3 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 rounded-lg font-medium"
                    >
                      {executing ? "Executing..." : "Execute Team"}
                    </button>
                  </>
                ) : (
                  <p className="text-slate-500 text-center py-8">
                    Select a team to manage
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Workspace Tab */}
        {activeTab === "workspace" && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Workflow Orchestration</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-700 rounded-lg p-4 text-center">
                <p className="text-3xl mb-2">📋</p>
                <p className="font-medium">Define Workflow</p>
                <p className="text-sm text-slate-400 mt-1">Create custom agent workflows</p>
              </div>
              <div className="bg-slate-700 rounded-lg p-4 text-center">
                <p className="text-3xl mb-2">🔄</p>
                <p className="font-medium">Orchestrate</p>
                <p className="text-sm text-slate-400 mt-1">Run multi-agent tasks</p>
              </div>
              <div className="bg-slate-700 rounded-lg p-4 text-center">
                <p className="text-3xl mb-2">📊</p>
                <p className="font-medium">Monitor</p>
                <p className="text-sm text-slate-400 mt-1">Track performance metrics</p>
              </div>
            </div>
            {result && (
              <div className="mt-6 p-4 bg-slate-700 rounded-lg">
                <p className="text-sm text-slate-400 mb-2">Execution Result</p>
                <pre className="text-sm overflow-x-auto">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
            {error && (
              <div className="mt-6 p-4 bg-red-900/50 border border-red-700 rounded-lg text-red-400">
                {error}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
