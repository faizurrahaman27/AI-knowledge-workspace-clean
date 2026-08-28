import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { login, loginWithGoogle, saveTokens } from "../api/auth";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function Login() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await login(formData);
      saveTokens(data);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Login Failed");
    } finally {
      setLoading(false);
    }
  };

  // Google Identity Services: only renders the button if a Client ID is
  // configured (VITE_GOOGLE_CLIENT_ID). Without one, this section simply
  // doesn't appear -- Google Sign-In is opt-in infrastructure, not a hard
  // requirement to use the app.
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => {
      window.google?.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          setError("");
          try {
            const data = await loginWithGoogle(response.credential);
            saveTokens(data);
            navigate("/dashboard");
          } catch (err) {
            setError(err.response?.data?.detail || "Google sign-in failed.");
          }
        },
      });
      window.google?.accounts.id.renderButton(
        document.getElementById("google-signin-button"),
        { theme: "outline", size: "large", width: 320 }
      );
    };
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-md bg-slate-800 rounded-xl shadow-xl p-6 sm:p-8">
        <h1 className="text-3xl font-bold text-white text-center">
          Production RAG Chatbot
        </h1>

        <p className="text-slate-400 text-center mt-2">Login to continue</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="Email"
            className="w-full p-3 rounded-lg bg-slate-700 text-white outline-none"
          />

          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="Password"
            className="w-full p-3 rounded-lg bg-slate-700 text-white outline-none"
          />

          {error && <p className="text-red-400">{error}</p>}

          <div className="text-right">
            <Link to="/forgot-password" className="text-sm text-blue-400 hover:text-blue-300">
              Forgot password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg font-semibold disabled:opacity-50"
          >
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>

        {GOOGLE_CLIENT_ID && (
          <div className="mt-6 flex flex-col items-center gap-3">
            <div className="w-full flex items-center gap-3 text-slate-500 text-xs">
              <div className="flex-1 h-px bg-slate-700" />
              OR
              <div className="flex-1 h-px bg-slate-700" />
            </div>
            <div id="google-signin-button" />
          </div>
        )}

        <p className="text-slate-400 text-center mt-6">
          Don't have an account?
          <Link to="/register" className="text-blue-400 ml-2">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
