import { Routes, Route } from "react-router-dom";

import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import ProtectedRoute from "./routes/ProtectedRoute";

// Feature pages - fully implemented
import Analytics from "./pages/Analytics";
import Research from "./pages/Research";
import Jobs from "./pages/Jobs";
import Exam from "./pages/Exam";
import Video from "./pages/Video";
import Math from "./pages/Math";
import Agents from "./pages/Agents";

export default function App() {
  return (
    <Routes>
      {/* Auth Routes */}
      <Route path="/" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* Main Application Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />

      {/* ============================================================================
          Future Module Routes (Scaffolded for easy addition)
          ========================================================================== */}
      
      {/* Research Module */}
      <Route
        path="/research"
        element={
          <ProtectedRoute>
            <Research />
          </ProtectedRoute>
        }
      />

      {/* Analytics Module */}
      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            <Analytics />
          </ProtectedRoute>
        }
      />

      {/* Job Hunting Module */}
      <Route
        path="/jobs"
        element={
          <ProtectedRoute>
            <Jobs />
          </ProtectedRoute>
        }
      />

      {/* Exam Preparation Module */}
      <Route
        path="/exam"
        element={
          <ProtectedRoute>
            <Exam />
          </ProtectedRoute>
        }
      />

      {/* Video Learning Module */}
      <Route
        path="/video"
        element={
          <ProtectedRoute>
            <Video />
          </ProtectedRoute>
        }
      />

      {/* Math & Science Module */}
      <Route
        path="/math"
        element={
          <ProtectedRoute>
            <Math />
          </ProtectedRoute>
        }
      />

      {/* Agent Studio Module */}
      <Route
        path="/agents"
        element={
          <ProtectedRoute>
            <Agents />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
