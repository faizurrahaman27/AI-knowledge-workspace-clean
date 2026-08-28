import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMe, changePassword, logoutEverywhere, clearTokens, saveTokens } from "../api/auth";
import { getActivityHistory, getSuggestions } from "../api/workspace";
import { useTheme } from "../context/ThemeContext";

export default function Profile() {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const [user, setUser] = useState(null);
  const [loadError, setLoadError] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwLoading, setPwLoading] = useState(false);
  const [pwMessage, setPwMessage] = useState("");
  const [pwError, setPwError] = useState("");

  const [logoutAllLoading, setLogoutAllLoading] = useState(false);

  const [activity, setActivity] = useState([]);
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setLoadError("Could not load your account. Try logging in again."));
    getActivityHistory().then(setActivity).catch(() => {});
    getSuggestions().then(setSuggestions).catch(() => {});
  }, []);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwLoading(true);
    setPwError("");
    setPwMessage("");
    try {
      const data = await changePassword(currentPassword, newPassword);
      saveTokens(data); // this session's tokens are refreshed automatically
      setCurrentPassword("");
      setNewPassword("");
      setPwMessage("Password updated.");
    } catch (err) {
      setPwError(err.response?.data?.detail || "Could not change password.");
    } finally {
      setPwLoading(false);
    }
  };

  const handleLogoutEverywhere = async () => {
    setLogoutAllLoading(true);
    try {
      await logoutEverywhere();
    } finally {
      clearTokens();
      navigate("/");
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white px-4 py-8">
      <div className="max-w-xl mx-auto">
        <button onClick={() => navigate("/dashboard")} className="text-blue-400 text-sm mb-4">
          ← Back to Dashboard
        </button>

        <h1 className="text-2xl font-bold mb-6">Profile & Settings</h1>

        {loadError && <p className="text-red-400">{loadError}</p>}

        {user && (
          <div className="bg-slate-800 rounded-xl p-6 mb-6">
            <h2 className="text-lg font-semibold mb-3">Account</h2>
            <p className="text-slate-300">
              <span className="text-slate-500">Name:</span> {user.full_name}
            </p>
            <p className="text-slate-300 mt-1">
              <span className="text-slate-500">Email:</span> {user.email}
            </p>
            <p className="text-slate-300 mt-1">
              <span className="text-slate-500">Role:</span> {user.role}
            </p>
            {!user.has_password && (
              <p className="text-slate-500 text-sm mt-3">
                This account signed in with Google and has no password set.
              </p>
            )}
          </div>
        )}

        <div className="bg-slate-800 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-3">Your Study Activity</h2>
          <p className="text-slate-500 text-sm mb-3">
            A history log, not AI-personalized recommendations — see README for what that
            distinction means here.
          </p>
          {activity.length === 0 ? (
            <p className="text-slate-500 text-sm">
              No study activity yet — try Study Mode or the AI Agent on a document.
            </p>
          ) : (
            <ul className="text-sm text-slate-300 space-y-1 max-h-48 overflow-y-auto">
              {activity.map((a) => (
                <li key={a.id} className="flex justify-between">
                  <span>
                    {a.mode} — {a.document_filename || `document #${a.document_id}`}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {suggestions.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-700">
              <h3 className="text-sm font-semibold text-slate-300 mb-2">Not studied yet</h3>
              <ul className="text-sm text-slate-400 space-y-1">
                {suggestions.map((s) => (
                  <li key={s.document_id}>{s.filename}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="bg-slate-800 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-3">Appearance</h2>
          <div className="flex items-center justify-between">
            <span className="text-slate-300">Theme</span>
            <button
              onClick={toggleTheme}
              className="bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded-lg text-sm"
            >
              {theme === "dark" ? "☀️ Switch to Light" : "🌙 Switch to Dark"}
            </button>
          </div>
        </div>

        {user?.has_password && (
          <div className="bg-slate-800 rounded-xl p-6 mb-6">
            <h2 className="text-lg font-semibold mb-3">Change Password</h2>
            <form onSubmit={handleChangePassword} className="space-y-3">
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Current password"
                className="w-full p-3 rounded-lg bg-slate-700 text-white outline-none text-sm"
                required
              />
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="New password"
                className="w-full p-3 rounded-lg bg-slate-700 text-white outline-none text-sm"
                required
              />
              {pwError && <p className="text-red-400 text-sm">{pwError}</p>}
              {pwMessage && <p className="text-green-400 text-sm">{pwMessage}</p>}
              <button
                type="submit"
                disabled={pwLoading}
                className="bg-blue-600 hover:bg-blue-700 px-5 py-2 rounded-lg text-sm disabled:opacity-50"
              >
                {pwLoading ? "Updating..." : "Update Password"}
              </button>
            </form>
          </div>
        )}

        <div className="bg-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-2">Security</h2>
          <p className="text-slate-400 text-sm mb-3">
            Sign out of this account on every device (browser sessions and any other logged-in
            device) at once.
          </p>
          <button
            onClick={handleLogoutEverywhere}
            disabled={logoutAllLoading}
            className="bg-red-600 hover:bg-red-700 px-5 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            {logoutAllLoading ? "Logging out..." : "Log out everywhere"}
          </button>
        </div>
      </div>
    </div>
  );
}
