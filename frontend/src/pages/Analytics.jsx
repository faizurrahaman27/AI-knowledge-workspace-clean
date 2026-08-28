import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from "recharts";
import api from "../api/axios";
import { getOverviewStats, getLearningAnalytics, getDocumentAnalytics, getEngagementMetrics } from "../api/analytics";

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"];

export default function Analytics() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [learning, setLearning] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [engagement, setEngagement] = useState(null);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState("week");

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewRes, learningRes, docsRes, engagementRes] = await Promise.allSettled([
        getOverviewStats(),
        getLearningAnalytics(),
        getDocumentAnalytics(),
        getEngagementMetrics(),
      ]);

      if (overviewRes.status === "fulfilled") setOverview(overviewRes.value.data);
      if (learningRes.status === "fulfilled") setLearning(learningRes.value.data);
      if (docsRes.status === "fulfilled") setDocuments(docsRes.value.data);
      if (engagementRes.status === "fulfilled") setEngagement(engagementRes.value.data);
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
      setError("Failed to load analytics. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 text-white p-8">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-slate-700 rounded w-1/4"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-32 bg-slate-800 rounded-xl"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 text-white p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-900/50 border border-red-700 rounded-xl p-6 text-center">
            <p className="text-red-400">{error}</p>
            <button onClick={fetchAnalytics} className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Generate mock data for demonstration if API doesn't return data
  const statsData = overview || {
    total_documents: 127,
    total_conversations: 843,
    active_workspaces: 12,
    learning_progress: 78,
  };

  const learningData = learning || [
    { day: "Mon", hours: 2.5, topics: 3 },
    { day: "Tue", hours: 1.8, topics: 2 },
    { day: "Wed", hours: 3.2, topics: 4 },
    { day: "Thu", hours: 2.1, topics: 3 },
    { day: "Fri", hours: 4.0, topics: 5 },
    { day: "Sat", hours: 1.5, topics: 2 },
    { day: "Sun", hours: 2.8, topics: 3 },
  ];

  const documentTypesData = documents?.types || [
    { name: "Research Papers", value: 35 },
    { name: "Books", value: 28 },
    { name: "Notes", value: 42 },
    { name: "Presentations", value: 15 },
    { name: "Other", value: 7 },
  ];

  const engagementData = engagement?.daily || [
    { date: "2024-01-01", sessions: 5, duration: 45 },
    { date: "2024-01-02", sessions: 8, duration: 72 },
    { date: "2024-01-03", sessions: 3, duration: 28 },
    { date: "2024-01-04", sessions: 6, duration: 55 },
    { date: "2024-01-05", sessions: 9, duration: 85 },
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold">Analytics Dashboard</h1>
            <p className="text-slate-400 mt-1">Track your learning progress and document insights</p>
          </div>
          <div className="flex gap-2">
            {["day", "week", "month", "year"].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-4 py-2 rounded-lg text-sm ${
                  timeRange === range
                    ? "bg-blue-600 text-white"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                }`}
              >
                {range.charAt(0).toUpperCase() + range.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Total Documents"
            value={statsData.total_documents || 0}
            icon="📄"
            trend="+12%"
            color="blue"
          />
          <StatCard
            title="Conversations"
            value={statsData.total_conversations || 0}
            icon="💬"
            trend="+8%"
            color="green"
          />
          <StatCard
            title="Active Workspaces"
            value={statsData.active_workspaces || 0}
            icon="📁"
            trend="+3"
            color="purple"
          />
          <StatCard
            title="Learning Progress"
            value={`${statsData.learning_progress || 0}%`}
            icon="📈"
            trend="+5%"
            color="amber"
          />
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Learning Hours Chart */}
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Study Time by Day</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={learningData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="day" stroke="#94A3B8" />
                  <YAxis stroke="#94A3B8" />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1E293B", border: "none", borderRadius: "8px" }}
                    labelStyle={{ color: "#E2E8F0" }}
                  />
                  <Bar dataKey="hours" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Document Types Pie Chart */}
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Document Distribution</h3>
            <div className="h-64 flex items-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={documentTypesData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {documentTypesData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1E293B", border: "none", borderRadius: "8px" }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {documentTypesData.map((item, index) => (
                  <div key={item.name} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <span className="text-sm text-slate-300">{item.name}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Engagement Trend */}
        <div className="bg-slate-800 rounded-xl p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4">Engagement Trend</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={engagementData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94A3B8" />
                <YAxis yAxisId="left" stroke="#94A3B8" />
                <YAxis yAxisId="right" orientation="right" stroke="#94A3B8" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1E293B", border: "none", borderRadius: "8px" }}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="sessions"
                  stroke="#10B981"
                  strokeWidth={2}
                  dot={{ fill: "#10B981" }}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="duration"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  dot={{ fill: "#F59E0B" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-1 bg-green-500 rounded"></div>
              <span className="text-sm text-slate-400">Sessions</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-1 bg-amber-500 rounded"></div>
              <span className="text-sm text-slate-400">Duration (min)</span>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-slate-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
          <div className="space-y-4">
            {[
              { time: "2 hours ago", action: "Document processed", detail: "Machine Learning Fundamentals.pdf", type: "success" },
              { time: "4 hours ago", action: "Quiz completed", detail: "Chapter 5 - Neural Networks", type: "info" },
              { time: "Yesterday", action: "Study session", detail: "45 minutes, 3 topics covered", type: "success" },
              { time: "Yesterday", action: "Flashcards reviewed", detail: "50 cards, 92% retention", type: "info" },
              { time: "2 days ago", action: "Workspace created", detail: "Research Project Alpha", type: "success" },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-4 p-3 bg-slate-700/50 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${
                  item.type === "success" ? "bg-green-500" : "bg-blue-500"
                }`}></div>
                <div className="flex-1">
                  <p className="font-medium">{item.action}</p>
                  <p className="text-sm text-slate-400">{item.detail}</p>
                </div>
                <span className="text-sm text-slate-500">{item.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, trend, color }) {
  const colorClasses = {
    blue: "bg-blue-500/20 text-blue-400",
    green: "bg-green-500/20 text-green-400",
    purple: "bg-purple-500/20 text-purple-400",
    amber: "bg-amber-500/20 text-amber-400",
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <div className="flex justify-between items-start mb-4">
        <span className="text-3xl">{icon}</span>
        <span className={`px-2 py-1 rounded text-xs ${trend.startsWith("+") ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
          {trend}
        </span>
      </div>
      <h3 className="text-2xl font-bold">{value}</h3>
      <p className="text-slate-400 text-sm mt-1">{title}</p>
    </div>
  );
}
