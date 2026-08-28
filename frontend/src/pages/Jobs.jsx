import { useState, useEffect } from "react";
import { getJobs, getJobs as fetchJobs } from "../api/jobs";
import api from "../api/axios";

const MOCK_JOBS = [
  { id: 1, title: "Senior ML Engineer", company: "TechCorp", location: "San Francisco, CA", salary: "$150K - $200K", type: "Full-time", skills: ["Python", "TensorFlow", "MLOps"] },
  { id: 2, title: "Data Scientist", company: "DataDriven Inc", location: "Remote", salary: "$120K - $160K", type: "Full-time", skills: ["Python", "SQL", "Statistics"] },
  { id: 3, title: "AI Research Intern", company: "AI Lab", location: "Boston, MA", salary: "$40K - $60K", type: "Internship", skills: ["Deep Learning", "NLP", "Research"] },
  { id: 4, title: "Product Manager - AI", company: "InnovateTech", location: "New York, NY", salary: "$140K - $180K", type: "Full-time", skills: ["Product Strategy", "AI/ML", "Agile"] },
  { id: 5, title: "NLP Engineer", company: "LanguageAI", location: "Austin, TX", salary: "$130K - $170K", type: "Full-time", skills: ["NLP", "Transformers", "Python"] },
];

export default function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [activeTab, setActiveTab] = useState("browse");
  const [searchQuery, setSearchQuery] = useState("");
  const [resumeFile, setResumeFile] = useState(null);
  const [analyzingResume, setAnalyzingResume] = useState(false);
  const [resumeAnalysis, setResumeAnalysis] = useState(null);

  useEffect(() => {
    fetchJobsData();
  }, []);

  const fetchJobsData = async () => {
    setLoading(true);
    try {
      const res = await fetchJobs();
      setJobs(res.data);
    } catch (err) {
      setJobs(MOCK_JOBS);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setResumeFile(file);
  };

  const analyzeResume = async () => {
    if (!resumeFile) return;
    setAnalyzingResume(true);
    // Simulate analysis
    setTimeout(() => {
      setResumeAnalysis({
        score: 85,
        matched_jobs: 12,
        top_skills: ["Python", "Machine Learning", "Data Analysis"],
        gaps: ["Kubernetes", "Spark"],
        recommendations: "Strong ML background. Consider adding more DevOps skills.",
      });
      setAnalyzingResume(false);
    }, 2000);
  };

  const filteredJobs = jobs.filter((job) =>
    job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    job.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
    job.skills.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold">Job Hunting</h1>
          <p className="text-slate-400 mt-1">Resume analysis, cover letter generation, and interview prep</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-slate-700 pb-2">
          {[
            { key: "browse", label: "Browse Jobs", icon: "🔍" },
            { key: "resume", label: "Resume Analysis", icon: "📄" },
            { key: "cover", label: "Cover Letters", icon: "✉️" },
            { key: "interview", label: "Interview Prep", icon: "🎯" },
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

        {/* Browse Jobs Tab */}
        {activeTab === "browse" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Job List */}
            <div className="lg:col-span-2 space-y-4">
              <div className="bg-slate-800 rounded-xl p-4">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search jobs by title, company, or skills..."
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {loading ? (
                <div className="text-center py-12 text-slate-400">Loading jobs...</div>
              ) : filteredJobs.length > 0 ? (
                filteredJobs.map((job) => (
                  <div
                    key={job.id}
                    onClick={() => setSelectedJob(job)}
                    className={`bg-slate-800 rounded-xl p-6 cursor-pointer transition ${
                      selectedJob?.id === job.id ? "ring-2 ring-blue-500" : "hover:bg-slate-700"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-lg font-semibold">{job.title}</h3>
                        <p className="text-slate-400">{job.company}</p>
                      </div>
                      <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">
                        {job.type}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-4 text-sm text-slate-400 mb-4">
                      <span>📍 {job.location}</span>
                      <span>💰 {job.salary}</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {job.skills.map((skill) => (
                        <span key={skill} className="px-2 py-1 bg-slate-700 rounded text-xs">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-slate-400">No jobs found</div>
              )}
            </div>

            {/* Job Detail */}
            <div className="lg:col-span-1">
              <div className="bg-slate-800 rounded-xl p-6 sticky top-4">
                {selectedJob ? (
                  <>
                    <h3 className="text-xl font-semibold mb-4">{selectedJob.title}</h3>
                    <p className="text-slate-400 mb-4">{selectedJob.company}</p>
                    
                    <div className="space-y-3 mb-6">
                      <div className="flex items-center gap-3">
                        <span>📍</span>
                        <span>{selectedJob.location}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span>💰</span>
                        <span>{selectedJob.salary}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span>⏰</span>
                        <span>{selectedJob.type}</span>
                      </div>
                    </div>

                    <div className="mb-6">
                      <p className="font-medium mb-2">Required Skills</p>
                      <div className="flex flex-wrap gap-2">
                        {selectedJob.skills.map((skill) => (
                          <span key={skill} className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>

                    <button className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium mb-2">
                      Apply Now
                    </button>
                    <button className="w-full py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium">
                      Generate Cover Letter
                    </button>
                  </>
                ) : (
                  <p className="text-slate-500 text-center py-12">
                    Select a job to view details
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Resume Analysis Tab */}
        {activeTab === "resume" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Upload Resume</h3>
              <div className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center mb-4">
                <input
                  type="file"
                  accept=".pdf,.doc,.docx"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="resume-upload"
                />
                <label htmlFor="resume-upload" className="cursor-pointer">
                  <p className="text-4xl mb-4">📄</p>
                  <p className="text-slate-300">
                    {resumeFile ? resumeFile.name : "Click to upload or drag and drop"}
                  </p>
                  <p className="text-sm text-slate-500 mt-2">PDF, DOC up to 10MB</p>
                </label>
              </div>
              <button
                onClick={analyzeResume}
                disabled={!resumeFile || analyzingResume}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-medium"
              >
                {analyzingResume ? "Analyzing..." : "Analyze Resume"}
              </button>
            </div>

            <div className="bg-slate-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Analysis Results</h3>
              {resumeAnalysis ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                    <span>ATS Score</span>
                    <span className="text-2xl font-bold text-green-400">{resumeAnalysis.score}%</span>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400 mb-2">Matched Jobs</p>
                    <p className="text-xl font-semibold">{resumeAnalysis.matched_jobs} positions</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400 mb-2">Top Skills</p>
                    <div className="flex flex-wrap gap-2">
                      {resumeAnalysis.top_skills.map((skill) => (
                        <span key={skill} className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400 mb-2">Skill Gaps</p>
                    <div className="flex flex-wrap gap-2">
                      {resumeAnalysis.gaps.map((skill) => (
                        <span key={skill} className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded text-xs">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="p-4 bg-blue-500/20 rounded-lg">
                    <p className="text-sm text-blue-400">{resumeAnalysis.recommendations}</p>
                  </div>
                </div>
              ) : (
                <p className="text-slate-500 text-center py-12">
                  Upload a resume to see analysis
                </p>
              )}
            </div>
          </div>
        )}

        {/* Cover Letters Tab */}
        {activeTab === "cover" && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Cover Letter Generator</h3>
            <p className="text-slate-400 mb-6">
              Generate personalized cover letters for your job applications.
              Select a job from the Browse tab or enter details below.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Company Name</label>
                <input
                  type="text"
                  placeholder="Company name"
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Position</label>
                <input
                  type="text"
                  placeholder="Job position"
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium mb-2">Key Points to Include</label>
                <textarea
                  placeholder="Why you're a great fit..."
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <button className="mt-6 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium">
              Generate Cover Letter
            </button>
          </div>
        )}

        {/* Interview Prep Tab */}
        {activeTab === "interview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {[
              { title: "Common Questions", icon: "❓", items: ["Tell me about yourself", "Why this company?", "Your strengths/weaknesses"] },
              { title: "Technical Questions", icon: "💻", items: ["System design", "Coding challenges", "ML fundamentals"] },
              { title: "Behavioral Questions", icon: "🧠", items: ["Team conflicts", "Leadership", "Problem-solving"] },
            ].map((section, i) => (
              <div key={i} className="bg-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl">{section.icon}</span>
                  <h3 className="text-lg font-semibold">{section.title}</h3>
                </div>
                <ul className="space-y-2">
                  {section.items.map((item, j) => (
                    <li key={j} className="flex items-center gap-2 text-slate-300">
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
                      {item}
                    </li>
                  ))}
                </ul>
                <button className="mt-4 w-full py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">
                  Practice
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
