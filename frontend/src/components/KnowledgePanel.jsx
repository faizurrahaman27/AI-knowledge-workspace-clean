"""
KnowledgePanel Component

React component for displaying extracted knowledge from documents.
Shows summaries, entities, concepts, relationships, questions, and flashcards.
"""

import { useState, useEffect } from "react";
import api from "../api/axios";

const KNOWLEDGE_TABS = [
  { key: "summary", label: "Summary", icon: "📝" },
  { key: "topics", label: "Topics", icon: "🏷️" },
  { key: "entities", label: "Entities", icon: "👤" },
  { key: "concepts", label: "Concepts", icon: "💡" },
  { key: "relationships", label: "Relationships", icon: "🔗" },
  { key: "questions", label: "Questions", icon: "❓" },
  { key: "flashcards", label: "Flashcards", icon: "🎴" },
  { key: "metadata", label: "Metadata", icon: "ℹ️" },
];

export default function KnowledgePanel({ document, onClose }) {
  const [activeTab, setActiveTab] = useState("summary");
  const [knowledge, setKnowledge] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [extractionStatus, setExtractionStatus] = useState(null);

  useEffect(() => {
    if (document) {
      fetchKnowledge();
    }
  }, [document]);

  const fetchKnowledge = async () => {
    if (!document) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Fetch extraction status
      const statusRes = await api.get(`/knowledge/${document.id}/extraction-status`);
      setExtractionStatus(statusRes.data);
      
      // If extraction is complete, fetch all knowledge
      if (statusRes.data.status === "completed") {
        const [summaryRes, topicsRes, entitiesRes, conceptsRes, 
               relRes, questionsRes, flashcardsRes, metadataRes] = await Promise.all([
          api.get(`/knowledge/${document.id}/summary`).catch(() => ({ data: null })),
          api.get(`/knowledge/${document.id}/topics`).catch(() => ({ data: [] })),
          api.get(`/knowledge/${document.id}/entities`).catch(() => ({ data: [] })),
          api.get(`/knowledge/${document.id}/concepts`).catch(() => ({ data: [] })),
          api.get(`/knowledge/${document.id}/relationships`).catch(() => ({ data: [] })),
          api.get(`/knowledge/${document.id}/questions`).catch(() => ({ data: [] })),
          api.get(`/knowledge/${document.id}/flashcards`).catch(() => ({ data: [] })),
          api.get(`/knowledge/${document.id}/metadata`).catch(() => ({ data: null })),
        ]);
        
        setKnowledge({
          summary: summaryRes.data,
          topics: topicsRes.data,
          entities: entitiesRes.data,
          concepts: conceptsRes.data,
          relationships: relRes.data,
          questions: questionsRes.data,
          flashcards: flashcardsRes.data,
          metadata: metadataRes.data,
        });
      }
    } catch (err) {
      console.error("Failed to fetch knowledge:", err);
      setError("Failed to load knowledge");
    } finally {
      setLoading(false);
    }
  };

  const triggerExtraction = async () => {
    if (!document) return;
    
    setLoading(true);
    try {
      await api.post(`/knowledge/${document.id}/extract`);
      // Poll for completion
      const poll = async () => {
        const statusRes = await api.get(`/knowledge/${document.id}/extraction-status`);
        if (statusRes.data.status === "completed") {
          fetchKnowledge();
          return;
        }
        if (statusRes.data.status === "in_progress") {
          setTimeout(poll, 2000);
        }
      };
      poll();
    } catch (err) {
      console.error("Extraction failed:", err);
      setError("Extraction failed");
    } finally {
      setLoading(false);
    }
  };

  const renderSummary = () => {
    if (!knowledge?.summary) return null;
    
    const { summary } = knowledge;
    
    return (
      <div className="space-y-4">
        {summary.one_sentence_summary && (
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-1">One-Sentence Summary</h4>
            <p className="text-white text-sm">{summary.one_sentence_summary}</p>
          </div>
        )}
        
        {summary.executive_summary && (
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-1">Executive Summary</h4>
            <p className="text-white text-sm whitespace-pre-wrap">{summary.executive_summary}</p>
          </div>
        )}
        
        {summary.bullet_summary && (
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-1">Key Points</h4>
            <div className="text-white text-sm whitespace-pre-wrap">{summary.bullet_summary}</div>
          </div>
        )}
        
        {summary.detailed_summary && (
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-1">Detailed Summary</h4>
            <p className="text-white text-sm whitespace-pre-wrap">{summary.detailed_summary}</p>
          </div>
        )}
      </div>
    );
  };

  const renderTopics = () => {
    if (!knowledge?.topics?.length) return null;
    
    return (
      <div className="space-y-3">
        {knowledge.topics.map((topic, idx) => (
          <div key={idx} className="p-3 bg-slate-700/50 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-2 py-0.5 text-xs rounded ${
                topic.topic_type === "primary" ? "bg-blue-600" : "bg-slate-600"
              }`}>
                {topic.topic_type}
              </span>
              <span className="font-medium text-white">{topic.topic_name}</span>
            </div>
            <div className="text-xs text-slate-400">
              {topic.category && <span>{topic.category}</span>}
              {topic.subcategory && <span> / {topic.subcategory}</span>}
            </div>
            {topic.related_topics?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {topic.related_topics.map((rt, i) => (
                  <span key={i} className="px-2 py-0.5 bg-slate-600/50 rounded text-xs text-slate-300">
                    {rt}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderEntities = () => {
    if (!knowledge?.entities?.length) return null;
    
    // Group by type
    const byType = knowledge.entities.reduce((acc, entity) => {
      if (!acc[entity.entity_type]) acc[entity.entity_type] = [];
      acc[entity.entity_type].push(entity);
      return acc;
    }, {});
    
    return (
      <div className="space-y-4">
        {Object.entries(byType).map(([type, entities]) => (
          <div key={type}>
            <h4 className="text-sm font-medium text-slate-300 mb-2 capitalize">
              {type.replace("_", " ")} ({entities.length})
            </h4>
            <div className="flex flex-wrap gap-2">
              {entities.map((entity, idx) => (
                <div
                  key={idx}
                  className="px-3 py-1.5 bg-slate-700/50 rounded-lg"
                  title={entity.description}
                >
                  <span className="text-sm text-white">{entity.name}</span>
                  {entity.mentions > 1 && (
                    <span className="ml-1 text-xs text-slate-400">×{entity.mentions}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderConcepts = () => {
    if (!knowledge?.concepts?.length) return null;
    
    return (
      <div className="space-y-3">
        {knowledge.concepts.map((concept, idx) => (
          <div key={idx} className="p-3 bg-slate-700/50 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-white">{concept.name}</span>
              <span className={`px-2 py-0.5 text-xs rounded ${
                concept.importance === "high" ? "bg-green-600" :
                concept.importance === "medium" ? "bg-yellow-600" : "bg-slate-600"
              }`}>
                {concept.importance}
              </span>
            </div>
            {concept.description && (
              <p className="text-xs text-slate-400 mt-1">{concept.description}</p>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderRelationships = () => {
    if (!knowledge?.relationships?.length) return null;
    
    return (
      <div className="space-y-2">
        {knowledge.relationships.map((rel, idx) => (
          <div key={idx} className="flex items-center gap-2 p-2 bg-slate-700/50 rounded">
            <span className="text-sm text-white font-medium">{rel.source_name}</span>
            <span className="px-2 py-0.5 bg-blue-600/50 rounded text-xs text-blue-300">
              {rel.relationship_type}
            </span>
            <span className="text-sm text-white">{rel.target_name}</span>
          </div>
        ))}
      </div>
    );
  };

  const renderQuestions = () => {
    if (!knowledge?.questions?.length) return null;
    
    return (
      <div className="space-y-4">
        {knowledge.questions.map((q, idx) => (
          <div key={idx} className="p-3 bg-slate-700/50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 text-xs rounded ${
                q.difficulty === "beginner" ? "bg-green-600" :
                q.difficulty === "intermediate" ? "bg-yellow-600" : "bg-red-600"
              }`}>
                {q.difficulty}
              </span>
              <span className="text-xs text-slate-400">{q.question_type.replace("_", " ")}</span>
            </div>
            <p className="text-white text-sm mb-2">{q.question_text}</p>
            {q.options && (
              <div className="space-y-1">
                {q.options.map((opt, i) => (
                  <div
                    key={i}
                    className={`text-sm px-2 py-1 rounded ${
                      i === q.correct_option_index
                        ? "bg-green-600/30 text-green-300"
                        : "bg-slate-600/50 text-slate-300"
                    }`}
                  >
                    {String.fromCharCode(65 + i)}. {opt}
                  </div>
                ))}
              </div>
            )}
            {q.answer && !q.options && (
              <p className="text-sm text-green-400 mt-2">Answer: {q.answer}</p>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderFlashcards = () => {
    if (!knowledge?.flashcards?.length) return null;
    
    return (
      <div className="space-y-3">
        {knowledge.flashcards.map((fc, idx) => (
          <div key={idx} className="p-3 bg-slate-700/50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 text-xs rounded ${
                fc.difficulty === "beginner" ? "bg-green-600" :
                fc.difficulty === "intermediate" ? "bg-yellow-600" : "bg-red-600"
              }`}>
                {fc.difficulty}
              </span>
              {fc.topic && <span className="text-xs text-slate-400">{fc.topic}</span>}
            </div>
            <p className="text-white text-sm font-medium mb-1">Q: {fc.front}</p>
            <p className="text-slate-300 text-sm">A: {fc.back}</p>
          </div>
        ))}
      </div>
    );
  };

  const renderMetadata = () => {
    if (!knowledge?.metadata) return null;
    
    const { metadata } = knowledge;
    
    return (
      <div className="space-y-3">
        {metadata.word_count && (
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Words</span>
            <span className="text-white">{metadata.word_count.toLocaleString()}</span>
          </div>
        )}
        {metadata.reading_time_minutes && (
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Reading Time</span>
            <span className="text-white">{metadata.reading_time_minutes} min</span>
          </div>
        )}
        {metadata.difficulty_score && (
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Difficulty</span>
            <span className="text-white">
              {(metadata.difficulty_score * 100).toFixed(0)}%
              <span className="text-slate-400 ml-1">
                ({metadata.difficulty_score < 0.4 ? "Easy" : 
                  metadata.difficulty_score < 0.7 ? "Medium" : "Hard"})
              </span>
            </span>
          </div>
        )}
        {metadata.document_category && (
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Category</span>
            <span className="text-white capitalize">{metadata.document_category}</span>
          </div>
        )}
        {metadata.academic_subject && (
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Subject</span>
            <span className="text-white">{metadata.academic_subject}</span>
          </div>
        )}
        <div className="border-t border-slate-700 pt-3 mt-3">
          <h4 className="text-sm font-medium text-slate-300 mb-2">Extraction Statistics</h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-slate-400">Entities</div>
            <div className="text-white">{metadata.entity_count || 0}</div>
            <div className="text-slate-400">Concepts</div>
            <div className="text-white">{metadata.concept_count || 0}</div>
            <div className="text-slate-400">Relationships</div>
            <div className="text-white">{metadata.relationship_count || 0}</div>
            <div className="text-slate-400">Questions</div>
            <div className="text-white">{metadata.question_count || 0}</div>
            <div className="text-slate-400">Flashcards</div>
            <div className="text-white">{metadata.flashcard_count || 0}</div>
          </div>
        </div>
      </div>
    );
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="text-center py-8">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={fetchKnowledge}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-white text-sm"
          >
            Retry
          </button>
        </div>
      );
    }

    if (extractionStatus?.status !== "completed") {
      return (
        <div className="text-center py-8">
          <p className="text-slate-400 mb-4">
            Knowledge extraction {extractionStatus?.status === "in_progress" ? "in progress..." : "not started"}
          </p>
          {extractionStatus?.status !== "in_progress" && (
            <button
              onClick={triggerExtraction}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white text-sm"
            >
              Start Extraction
            </button>
          )}
        </div>
      );
    }

    switch (activeTab) {
      case "summary": return renderSummary();
      case "topics": return renderTopics();
      case "entities": return renderEntities();
      case "concepts": return renderConcepts();
      case "relationships": return renderRelationships();
      case "questions": return renderQuestions();
      case "flashcards": return renderFlashcards();
      case "metadata": return renderMetadata();
      default: return null;
    }
  };

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-slate-800 border-l border-slate-700 shadow-xl z-50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Knowledge</h2>
        <button
          onClick={onClose}
          className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white"
        >
          ✕
        </button>
      </div>
      
      {/* Tabs */}
      <div className="flex flex-wrap gap-1 p-2 border-b border-slate-700">
        {KNOWLEDGE_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
              activeTab === tab.key
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-white hover:bg-slate-700"
            }`}
            title={tab.label}
          >
            <span>{tab.icon}</span>
          </button>
        ))}
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {renderContent()}
      </div>
    </div>
  );
}
