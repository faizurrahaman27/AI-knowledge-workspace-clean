import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api/auth";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-md bg-slate-800 rounded-xl shadow-xl p-6 sm:p-8">
        <h1 className="text-2xl font-bold text-white text-center">Reset your password</h1>

        {sent ? (
          <p className="text-slate-300 text-center mt-6">
            If that email is registered, a reset link has been sent. (No email service is
            configured yet in this deployment? Ask your admin to check the server logs — the
            link is printed there in dev mode.)
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Your account email"
              className="w-full p-3 rounded-lg bg-slate-700 text-white outline-none"
              required
            />
            {error && <p className="text-red-400">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg font-semibold disabled:opacity-50"
            >
              {loading ? "Sending..." : "Send reset link"}
            </button>
          </form>
        )}

        <p className="text-slate-400 text-center mt-6">
          <Link to="/" className="text-blue-400">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}
