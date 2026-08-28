import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { register } from "../api/auth";

export default function Register() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password: "",
  });

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
      await register(formData);
      navigate("/", { state: { justRegistered: true } });
    } catch (err) {
      const detail = err.response?.data?.detail;
      // FastAPI validation errors come back as a list of {msg, ...}; a
      // plain string detail is a normal application error.
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(" ")
        : detail;
      setError(message || "Registration Failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-md bg-slate-800 rounded-xl shadow-xl p-6 sm:p-8">
        <h1 className="text-3xl font-bold text-white text-center">Create Account</h1>
        <p className="text-slate-400 text-center mt-2">Join Production RAG Chatbot</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <input
            type="text"
            name="full_name"
            value={formData.full_name}
            onChange={handleChange}
            placeholder="Full name"
            className="w-full p-3 rounded-lg bg-slate-700 text-white outline-none"
            required
          />

          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="Email"
            className="w-full p-3 rounded-lg bg-slate-700 text-white outline-none"
            required
          />

          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="Password (8+ chars, upper/lower/digit)"
            className="w-full p-3 rounded-lg bg-slate-700 text-white outline-none"
            required
          />

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-green-600 hover:bg-green-700 text-white p-3 rounded-lg font-semibold disabled:opacity-50"
          >
            {loading ? "Creating Account..." : "Register"}
          </button>
        </form>

        <p className="text-slate-400 text-center mt-6">
          Already have an account?
          <Link to="/" className="text-blue-400 ml-2">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}
