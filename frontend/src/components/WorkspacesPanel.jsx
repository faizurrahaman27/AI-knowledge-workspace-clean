import { useEffect, useState } from "react";
import {
  createTeam, listTeams, inviteToTeam, listTeamMembers,
  createWorkspace, listWorkspaces, addDocumentToWorkspace, removeDocumentFromWorkspace,
  listWorkspaceDocuments,
} from "../api/workspace";

export default function WorkspacesPanel({ documents, onWorkspacesChanged }) {
  const [teams, setTeams] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedTeamId, setSelectedTeamId] = useState(null);
  const [members, setMembers] = useState([]);

  const [newTeamName, setNewTeamName] = useState("");
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [newWorkspaceTeam, setNewWorkspaceTeam] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");

  const [expandedWorkspace, setExpandedWorkspace] = useState(null);
  const [workspaceDocs, setWorkspaceDocs] = useState({});
  const [addDocSelection, setAddDocSelection] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    try {
      const [t, w] = await Promise.all([listTeams(), listWorkspaces()]);
      setTeams(t);
      setWorkspaces(w);
      onWorkspacesChanged?.(w);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load workspaces/teams.");
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!selectedTeamId) {
      setMembers([]);
      return;
    }
    listTeamMembers(selectedTeamId).then(setMembers).catch(() => setMembers([]));
  }, [selectedTeamId]);

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    if (!newTeamName.trim()) return;
    setLoading(true);
    setError("");
    try {
      await createTeam(newTeamName.trim());
      setNewTeamName("");
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create team.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkspace = async (e) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    setLoading(true);
    setError("");
    try {
      await createWorkspace(newWorkspaceName.trim(), newWorkspaceTeam || null);
      setNewWorkspaceName("");
      setNewWorkspaceTeam("");
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create workspace.");
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!selectedTeamId || !inviteEmail.trim()) return;
    setError("");
    try {
      await inviteToTeam(selectedTeamId, inviteEmail.trim());
      setInviteEmail("");
      alert(
        `Invite sent to ${inviteEmail}. If no email server is configured, ` +
        `ask your admin to check the server logs for the invite link.`
      );
    } catch (err) {
      setError(err.response?.data?.detail || "Could not send invite.");
    }
  };

  const toggleWorkspaceDocs = async (workspaceId) => {
    if (expandedWorkspace === workspaceId) {
      setExpandedWorkspace(null);
      return;
    }
    setExpandedWorkspace(workspaceId);
    if (!workspaceDocs[workspaceId]) {
      try {
        const docs = await listWorkspaceDocuments(workspaceId);
        setWorkspaceDocs((prev) => ({ ...prev, [workspaceId]: docs }));
      } catch {
        setWorkspaceDocs((prev) => ({ ...prev, [workspaceId]: [] }));
      }
    }
  };

  const handleAddDoc = async (workspaceId) => {
    if (!addDocSelection) return;
    try {
      await addDocumentToWorkspace(workspaceId, Number(addDocSelection));
      const docs = await listWorkspaceDocuments(workspaceId);
      setWorkspaceDocs((prev) => ({ ...prev, [workspaceId]: docs }));
      setAddDocSelection("");
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not add document.");
    }
  };

  const handleRemoveDoc = async (workspaceId, documentId) => {
    try {
      await removeDocumentFromWorkspace(workspaceId, documentId);
      const docs = await listWorkspaceDocuments(workspaceId);
      setWorkspaceDocs((prev) => ({ ...prev, [workspaceId]: docs }));
      await refresh();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not remove document.");
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-900/40 border border-red-700 rounded-lg px-4 py-2 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Teams */}
      <div className="bg-slate-800 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-1">Teams</h2>
        <p className="text-slate-400 text-sm mb-4">
          Create a team, invite members by email, and give the team shared workspaces.
        </p>

        <form onSubmit={handleCreateTeam} className="flex flex-wrap gap-2 mb-4">
          <input
            value={newTeamName}
            onChange={(e) => setNewTeamName(e.target.value)}
            placeholder="Team name"
            className="flex-1 min-w-[160px] p-2 rounded-lg bg-slate-700 text-white text-sm outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-white text-sm disabled:opacity-50"
          >
            Create Team
          </button>
        </form>

        <div className="flex flex-wrap gap-2 mb-4">
          {teams.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelectedTeamId(t.id === selectedTeamId ? null : t.id)}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                selectedTeamId === t.id ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-300"
              }`}
            >
              {t.name} <span className="text-xs opacity-70">({t.role})</span>
            </button>
          ))}
          {teams.length === 0 && <p className="text-slate-500 text-sm">No teams yet.</p>}
        </div>

        {selectedTeamId && (
          <div className="bg-slate-900 rounded-lg p-4">
            <h3 className="text-white text-sm font-semibold mb-2">Members</h3>
            <ul className="text-sm text-slate-300 space-y-1 mb-4">
              {members.map((m) => (
                <li key={m.user_id} className="flex justify-between">
                  <span>{m.full_name} ({m.email})</span>
                  <span className="text-slate-500 capitalize">{m.role}</span>
                </li>
              ))}
            </ul>

            <form onSubmit={handleInvite} className="flex flex-wrap gap-2">
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="Invite by email"
                className="flex-1 min-w-[160px] p-2 rounded-lg bg-slate-700 text-white text-sm outline-none"
              />
              <button
                type="submit"
                className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-white text-sm"
              >
                Invite
              </button>
            </form>
          </div>
        )}
      </div>

      {/* Workspaces */}
      <div className="bg-slate-800 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-1">Workspaces</h2>
        <p className="text-slate-400 text-sm mb-4">
          Group documents together for multi-document chat. Personal workspaces are yours alone;
          team workspaces are shared — every team member sees the same documents and the same
          chat thread live (see the Chat tab's workspace selector).
        </p>

        <form onSubmit={handleCreateWorkspace} className="flex flex-wrap gap-2 mb-4">
          <input
            value={newWorkspaceName}
            onChange={(e) => setNewWorkspaceName(e.target.value)}
            placeholder="Workspace name"
            className="flex-1 min-w-[160px] p-2 rounded-lg bg-slate-700 text-white text-sm outline-none"
          />
          <select
            value={newWorkspaceTeam}
            onChange={(e) => setNewWorkspaceTeam(e.target.value)}
            className="p-2 rounded-lg bg-slate-700 text-white text-sm"
          >
            <option value="">Personal (just me)</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                Team: {t.name}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-white text-sm disabled:opacity-50"
          >
            Create Workspace
          </button>
        </form>

        <div className="space-y-3">
          {workspaces.map((ws) => (
            <div key={ws.id} className="bg-slate-900 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-white font-medium">{ws.name}</span>
                  <span className="text-slate-500 text-xs ml-2">
                    {ws.team_id ? "Team workspace" : "Personal"} · {ws.document_count} document(s)
                  </span>
                </div>
                <button
                  onClick={() => toggleWorkspaceDocs(ws.id)}
                  className="text-blue-400 hover:text-blue-300 text-sm"
                >
                  {expandedWorkspace === ws.id ? "Hide" : "Manage documents"}
                </button>
              </div>

              {expandedWorkspace === ws.id && (
                <div className="mt-3 pt-3 border-t border-slate-700">
                  <ul className="text-sm text-slate-300 space-y-1 mb-3">
                    {(workspaceDocs[ws.id] || []).map((d) => (
                      <li key={d.id} className="flex justify-between items-center">
                        <span>{d.filename}</span>
                        <button
                          onClick={() => handleRemoveDoc(ws.id, d.id)}
                          className="text-red-400 hover:text-red-300 text-xs"
                        >
                          Remove
                        </button>
                      </li>
                    ))}
                    {(workspaceDocs[ws.id] || []).length === 0 && (
                      <li className="text-slate-500">No documents yet.</li>
                    )}
                  </ul>

                  <div className="flex gap-2">
                    <select
                      value={addDocSelection}
                      onChange={(e) => setAddDocSelection(e.target.value)}
                      className="flex-1 p-2 rounded-lg bg-slate-700 text-white text-sm"
                    >
                      <option value="">Add a document...</option>
                      {documents
                        .filter((d) => !(workspaceDocs[ws.id] || []).some((wd) => wd.id === d.id))
                        .map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.filename}
                          </option>
                        ))}
                    </select>
                    <button
                      onClick={() => handleAddDoc(ws.id)}
                      className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-white text-sm"
                    >
                      Add
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
          {workspaces.length === 0 && <p className="text-slate-500 text-sm">No workspaces yet.</p>}
        </div>
      </div>
    </div>
  );
}
