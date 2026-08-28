import { useNavigate } from "react-router-dom";
import { clearTokens } from "../api/auth";
import { useTheme } from "../context/ThemeContext";

// Module quick links configuration
const MODULE_LINKS = [
  { path: "/dashboard", icon: "📄", label: "Documents" },
  { path: "/research", icon: "📚", label: "Research" },
  { path: "/analytics", icon: "📊", label: "Analytics" },
  { path: "/jobs", icon: "💼", label: "Jobs" },
  { path: "/exam", icon: "📝", label: "Exam" },
  { path: "/video", icon: "🎬", label: "Video" },
  { path: "/math", icon: "🔢", label: "Math" },
  { path: "/agents", icon: "🤖", label: "Agents" },
];

export default function Navbar({ onMenuClick }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const handleLogout = () => {
    clearTokens();
    navigate("/");
  };

  return (
    <div className="h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-4 sm:px-6">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          className="lg:hidden text-white p-1"
          aria-label="Open menu"
        >
          ☰
        </button>
        <h1 className="text-white text-lg sm:text-xl font-bold truncate">
          AI Knowledge Workspace
        </h1>
      </div>

      {/* Module Quick Links */}
      <div className="hidden md:flex items-center gap-1 mr-4">
        {MODULE_LINKS.map((link) => (
          <button
            key={link.path}
            onClick={() => navigate(link.path)}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-700 transition-colors"
            title={link.label}
          >
            <span title={link.label}>{link.icon}</span>
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        <button
          onClick={toggleTheme}
          className="text-white p-2 rounded-lg hover:bg-slate-700"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? "☀️" : "🌙"}
        </button>

        <button
          onClick={() => navigate("/profile")}
          className="text-white p-2 rounded-lg hover:bg-slate-700"
          title="Profile & settings"
        >
          👤
        </button>

        <button
          onClick={handleLogout}
          className="bg-red-500 hover:bg-red-600 px-3 sm:px-4 py-2 rounded text-white text-sm"
        >
          Logout
        </button>
      </div>
    </div>
  );
}
