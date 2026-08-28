# Phase 8: Autonomous Learning System

## Architecture Documentation

**Date:** 2026-07-19  
**Phase:** 8 - Autonomous Learning System  
**Status:** Complete

---

## Executive Summary

Phase 8 transforms the AI Knowledge Workspace into a complete autonomous knowledge understanding system. The system deeply understands everything inside the workspace and continuously organizes knowledge automatically—significantly more intelligent than NotebookLM.

### Key Features

- **Knowledge Graph Engine**: Persistent knowledge graph with automatic entity and relationship discovery
- **Intelligent Notebooks**: Living knowledge bases with auto-generated content
- **Learning Path Engine**: Automatic learning path generation
- **Knowledge Insights**: Auto-generated insights and recommendations
- **AI Memory**: Long-term memory for workspace understanding
- **Background Workers**: Async autonomous processing infrastructure
- **Document Evolution**: Version tracking for knowledge changes

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Autonomous Learning System                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Knowledge Graph Engine                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ Entities │  │Concepts  │  │People   │  │Technologies│          │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │   │
│  │       └────────────┴────────────┴────────────┘                        │   │
│  │                          │                                            │   │
│  │       ┌─────────────────┼─────────────────┐                            │   │
│  │       ↓                 ↓                 ↓                            │   │
│  │  ┌─────────┐     ┌─────────┐     ┌─────────┐                        │   │
│  │  │Relations│     │Paths    │     │Subgraphs│                        │   │
│  │  └─────────┘     └─────────┘     └─────────┘                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Intelligent Notebooks                            │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │Auto Summary│  │Timeline  │  │Concept Map│  │Quotations │    │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │Mind Map   │  │Questions │  │Flashcards │  │Insights  │    │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Learning Path Engine                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │Prerequisites│ │Steps │  │Progress │  │Recommendations│          │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     AI Memory                                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │Conversations│ │Workspace│  │Research │  │Discoveries│           │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Background Workers                                │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │Extract  │  │Embed    │  │Validate │  │Analyze │           │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### knowledge_nodes

```sql
CREATE TABLE knowledge_nodes (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    aliases JSONB,
    language VARCHAR(10) DEFAULT 'en',
    source_document_id INTEGER REFERENCES documents(id),
    source_chunk_id INTEGER,
    citation TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    importance_score FLOAT DEFAULT 0.5,
    embedding_vector JSONB,
    in_degree INTEGER DEFAULT 0,
    out_degree INTEGER DEFAULT 0,
    first_seen_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_knowledge_nodes_user ON knowledge_nodes(user_id);
CREATE INDEX ix_knowledge_nodes_type ON knowledge_nodes(entity_type);
```

### knowledge_edges

```sql
CREATE TABLE knowledge_edges (
    id SERIAL PRIMARY KEY,
    edge_id VARCHAR(100) UNIQUE NOT NULL,
    source_node_id INTEGER REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    target_node_id INTEGER REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    description TEXT,
    weight FLOAT DEFAULT 1.0,
    source_document_id INTEGER REFERENCES documents(id),
    citation TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    is_auto_generated BOOLEAN DEFAULT TRUE,
    is_validated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_knowledge_edges_source ON knowledge_edges(source_node_id);
CREATE INDEX ix_knowledge_edges_target ON knowledge_edges(target_node_id);
```

### intelligent_notebooks

```sql
CREATE TABLE intelligent_notebooks (
    id SERIAL PRIMARY KEY,
    notebook_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    document_ids JSONB,
    concept_ids JSONB,
    entity_ids JSONB,
    auto_summary TEXT,
    auto_timeline JSONB,
    auto_concept_map JSONB,
    auto_quotations JSONB,
    auto_mind_map JSONB,
    document_count INTEGER DEFAULT 0,
    concept_count INTEGER DEFAULT 0,
    entity_count INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0,
    flashcard_count INTEGER DEFAULT 0,
    knowledge_confidence FLOAT DEFAULT 0.0,
    coverage_score FLOAT DEFAULT 0.0,
    is_public BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### learning_paths

```sql
CREATE TABLE learning_paths (
    id SERIAL PRIMARY KEY,
    path_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    topic VARCHAR(200) NOT NULL,
    prerequisites JSONB,
    steps JSONB,
    dependencies JSONB,
    total_estimated_hours FLOAT DEFAULT 0.0,
    difficulty_level VARCHAR(20) DEFAULT 'intermediate',
    completion_percentage FLOAT DEFAULT 0.0,
    recommended_documents JSONB,
    recommended_videos JSONB,
    recommended_repositories JSONB,
    recommended_books JSONB,
    recommended_papers JSONB,
    completed_steps JSONB,
    current_step INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### knowledge_insights

```sql
CREATE TABLE knowledge_insights (
    id SERIAL PRIMARY KEY,
    insight_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    insight_type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    related_node_ids JSONB,
    related_document_ids JSONB,
    importance_score FLOAT DEFAULT 0.5,
    confidence_score FLOAT DEFAULT 0.5,
    generated_by VARCHAR(50),
    generation_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### ai_memory

```sql
CREATE TABLE ai_memory (
    id SERIAL PRIMARY KEY,
    memory_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    workspace_id INTEGER REFERENCES workspaces(id),
    memory_type VARCHAR(50) NOT NULL,
    key VARCHAR(200) NOT NULL,
    value TEXT NOT NULL,
    summary TEXT,
    tags JSONB,
    importance_score FLOAT DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_ai_memory_user ON ai_memory(user_id);
CREATE INDEX ix_ai_memory_type ON ai_memory(memory_type);
```

### background_jobs

```sql
CREATE TABLE background_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    job_name VARCHAR(200) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(50),
    target_id VARCHAR(100),
    input_data JSONB,
    output_data JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    progress FLOAT DEFAULT 0.0,
    current_step VARCHAR(100),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    priority INTEGER DEFAULT 5,
    estimated_duration_seconds INTEGER,
    actual_duration_seconds INTEGER,
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_background_jobs_status ON background_jobs(status);
```

### document_versions

```sql
CREATE TABLE document_versions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    snapshot_data JSONB,
    previous_snapshot JSONB,
    changes JSONB,
    diff_summary TEXT,
    entity_count_before INTEGER DEFAULT 0,
    entity_count_after INTEGER DEFAULT 0,
    concept_count_before INTEGER DEFAULT 0,
    concept_count_after INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### learning_progress

```sql
CREATE TABLE learning_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    topic VARCHAR(200) NOT NULL,
    comprehension_level FLOAT DEFAULT 0.0,
    practice_count INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    next_review_at TIMESTAMP,
    ease_factor FLOAT DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    is_mastered BOOLEAN DEFAULT FALSE,
    mastered_at TIMESTAMP,
    started_at TIMESTAMP,
    last_practiced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, topic)
);
```

---

## API Endpoints

### Knowledge Graph

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/autonomous/graph/stats` | Graph statistics |
| GET | `/autonomous/graph/nodes` | List nodes |
| GET | `/autonomous/graph/nodes/{id}` | Node details |
| GET | `/autonomous/graph/subgraph/{id}` | Subgraph |
| GET | `/autonomous/graph/path` | Find path |
| GET | `/autonomous/graph/connected/{id}` | Connected nodes |
| POST | `/autonomous/graph/build/{doc_id}` | Build from document |

### Intelligent Notebooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/autonomous/notebooks` | Create notebook |
| GET | `/autonomous/notebooks` | List notebooks |
| GET | `/autonomous/notebooks/{id}` | Notebook details |
| POST | `/autonomous/notebooks/{id}/documents/{doc_id}` | Add document |
| POST | `/autonomous/notebooks/{id}/generate` | Generate content |

### Learning Paths

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/autonomous/learning-paths` | Create path |
| GET | `/autonomous/learning-paths` | List paths |
| GET | `/autonomous/learning-paths/{id}` | Path details |
| POST | `/autonomous/learning-paths/{id}/generate` | Generate steps |
| PUT | `/autonomous/learning-paths/{id}/progress` | Update progress |

### Insights

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/autonomous/insights` | Get insights |

### Background Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/autonomous/jobs` | List jobs |
| GET | `/autonomous/jobs/{id}` | Job details |
| POST | `/autonomous/jobs/{id}/retry` | Retry job |
| POST | `/autonomous/jobs/{id}/cancel` | Cancel job |

---

## Services

### KnowledgeGraphService

- Node creation and management
- Edge creation and relationship building
- Automatic entity extraction
- Duplicate detection
- Graph traversal
- Path finding
- Subgraph extraction
- Graph statistics

### IntelligentNotebookService

- Notebook creation and management
- Auto-generated summaries
- Timeline generation
- Concept map generation
- Quotation extraction
- Knowledge insights

### LearningPathService

- Path creation
- Step generation
- Progress tracking
- Recommendations

### InsightService

- Important topics identification
- Connected concepts
- Knowledge gaps
- Learning progress

### BackgroundWorker

- Job queuing
- Progress tracking
- Retry logic
- Priority scheduling
- Status updates

---

## Entity Types

- person
- company
- technology
- library
- country
- organization
- topic
- skill
- algorithm
- programming_language
- framework
- date
- event
- concept

## Relationship Types

- depends_on
- related_to
- part_of
- implements
- uses
- contradicts
- supports
- references
- defines
- extends
- precedes
- leads_to

---

## Background Job Types

- extract_knowledge
- generate_embeddings
- build_knowledge_graph
- generate_questions
- generate_flashcards
- create_notebook
- update_timeline
- generate_summary
- validate_knowledge
- analyze_document

---

## Integration with Previous Phases

### Knowledge Intelligence (Phase 3)
- Consumes extracted entities
- Consumes extracted concepts
- Builds knowledge graph

### Validation Layer (Phase 3.5)
- Validates knowledge quality
- Checks consistency

### Interaction Layer (Phase 4)
- Notebooks integrate with notes
- Flashcards link to flashcards

### Research OS (Phase 5)
- Research uses knowledge graph
- Insights influence research

### Multi-Agent (Phase 6)
- Agents use knowledge graph
- Background workers process

### Multilingual (Phase 7)
- Knowledge graph supports all languages
- Notebooks multilingual

---

## Files Added

```
backend/src/autonomous/
├── __init__.py
├── models.py
├── api/
│   └── autonomous.py
└── services/
    ├── __init__.py
    ├── knowledge_graph.py
    ├── notebook.py
    └── workers.py

docs/architecture/
└── phase-8-autonomous-learning.md
```

---

## Git Commit Summary

```
Phase 8: Autonomous Learning System

## Database Models (8 tables)
- knowledge_nodes: Knowledge graph entities
- knowledge_edges: Knowledge graph relationships
- intelligent_notebooks: Auto-generated notebooks
- learning_paths: Learning path tracking
- knowledge_insights: Generated insights
- ai_memory: Long-term AI memory
- background_jobs: Async job processing
- learning_progress: Spaced repetition tracking
- document_versions: Knowledge evolution

## Services (5 services)
- KnowledgeGraphService: Graph engine
- IntelligentNotebookService: Notebook management
- LearningPathService: Learning paths
- InsightService: Knowledge insights
- BackgroundWorker: Async processing

## API Endpoints (25+ endpoints)
- /autonomous/graph: Knowledge graph
- /autonomous/notebooks: Intelligent notebooks
- /autonomous/learning-paths: Learning paths
- /autonomous/insights: Insights
- /autonomous/jobs: Background jobs

## Key Features
- Persistent knowledge graph
- Automatic entity extraction
- Automatic relationship discovery
- Duplicate detection
- Subgraph extraction
- Path finding
- Intelligent notebooks
- Auto-generated content
- Learning path generation
- Knowledge insights
- AI memory
- Background workers
- Spaced repetition
- Document evolution tracking
```
