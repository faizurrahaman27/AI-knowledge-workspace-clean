# Phase 5: Research Operating System (ResearchOS)

## Architecture Documentation

**Date:** 2026-07-19  
**Phase:** 5 - Research Operating System  
**Status:** Complete

---

## Executive Summary

Phase 5 transforms the AI Knowledge Workspace into an enterprise-grade Research Operating System (ResearchOS). The system performs structured AI-assisted research, consuming validated knowledge from previous phases and producing reusable research outputs.

### Key Features

- **Research Projects**: Organize research goals and findings
- **Research Planner**: Generate structured plans from goals
- **Task Decomposition**: Break complex goals into subtasks
- **Evidence Collection**: Collect from workspace and external sources
- **Source Verification**: Evaluate authority, freshness, credibility
- **Evidence Ranking**: Multi-factor ranking algorithm
- **Conflict Detection**: Detect conflicting claims and information
- **Knowledge Synthesis**: Generate structured knowledge from evidence
- **Report Generation**: Produce comprehensive research reports
- **Export Options**: Markdown, HTML, Notebook integration

---

## Research Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Research Operating System                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Goal                                                                   │
│      ↓                                                                      │
│  ┌─────────────────┐                                                        │
│  │ Research Planner │                                                        │
│  │  - Objectives   │                                                        │
│  │  - Questions    │                                                        │
│  │  - Tasks        │                                                        │
│  └────────┬────────┘                                                        │
│           ↓                                                                 │
│  ┌─────────────────┐                                                        │
│  │Task Decomposer  │                                                        │
│  │  - Subtasks     │                                                        │
│  │  - Priorities   │                                                        │
│  └────────┬────────┘                                                        │
│           ↓                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐         │
│  │                     Evidence Collection                           │         │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │         │
│  │  │Workspace │  │Web Pages │  │GitHub    │  │ ArXiv    │    │         │
│  │  │Documents │  │          │  │Repos     │  │Papers   │    │         │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │         │
│  └────────────────────────────────┬────────────────────────────────┘         │
│                                   ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐         │
│  │                   Source Verification                              │         │
│  │  Authority Score | Freshness Score | Credibility Score             │         │
│  └────────────────────────────────┬────────────────────────────────┘         │
│                                   ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐         │
│  │                   Evidence Ranking                                │         │
│  │  Relevance (30%) | Credibility (25%) | Authority (20%)              │         │
│  │  Freshness (15%) | Popularity (10%)                               │         │
│  └────────────────────────────────┬────────────────────────────────┘         │
│                                   ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐         │
│  │                   Conflict Detection                              │         │
│  │  Claims | Definitions | Dates | Metrics | Conclusions               │         │
│  └────────────────────────────────┬────────────────────────────────┘         │
│                                   ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐         │
│  │                   Knowledge Synthesis                             │         │
│  │  Summary | Comparison | Pros/Cons | Consensus | Questions          │         │
│  └────────────────────────────────┬────────────────────────────────┘         │
│                                   ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐         │
│  │                   Report Generation                               │         │
│  │  Executive | Technical | Beginner | References                     │         │
│  └────────────────────────────────┬────────────────────────────────┘         │
│                                   ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐         │
│  │                   Notebook Integration                             │         │
│  │  Notes | Collections | Activity | Pins                             │         │
│  └─────────────────────────────────────────────────────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Research Projects Table

```sql
CREATE TABLE research_projects (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    objective TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    scope TEXT,
    keywords JSONB,
    tags JSONB,
    status VARCHAR(20) DEFAULT 'planning',
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    progress_percentage FLOAT DEFAULT 0,
    overall_confidence FLOAT,
    evidence_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Research Tasks Table

```sql
CREATE TABLE research_tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    task_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    parent_task_id INTEGER REFERENCES research_tasks(id) ON DELETE CASCADE,
    assigned_agent VARCHAR(100),
    estimated_duration_minutes INTEGER,
    actual_duration_minutes INTEGER,
    findings JSONB,
    blockers TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Research Evidence Table

```sql
CREATE TABLE research_evidence (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES research_tasks(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    content TEXT,
    source_type VARCHAR(50) NOT NULL,
    source_url VARCHAR(1000),
    source_name VARCHAR(500),
    author VARCHAR(500),
    publication VARCHAR(500),
    published_date TIMESTAMP,
    citation_key VARCHAR(100),
    authority_score FLOAT,
    freshness_score FLOAT,
    popularity_score FLOAT,
    workspace_trust BOOLEAN DEFAULT FALSE,
    validation_confidence VARCHAR(20) DEFAULT 'unknown',
    relevance_score FLOAT DEFAULT 0,
    credibility_score FLOAT DEFAULT 0,
    overall_score FLOAT DEFAULT 0,
    linked_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    citations JSONB,
    is_validated BOOLEAN DEFAULT FALSE,
    is_pertinent BOOLEAN DEFAULT TRUE,
    retrieval_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Research Conflicts Table

```sql
CREATE TABLE research_conflicts (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id) ON DELETE CASCADE,
    conflict_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    evidence_a_id INTEGER REFERENCES research_evidence(id) ON DELETE SET NULL,
    evidence_b_id INTEGER REFERENCES research_evidence(id) ON DELETE SET NULL,
    resolution_status VARCHAR(20) DEFAULT 'unresolved',
    resolution_notes TEXT,
    resolved_by VARCHAR(100),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Research Reports Table

```sql
CREATE TABLE research_reports (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    report_type VARCHAR(50) DEFAULT 'comprehensive',
    version INTEGER DEFAULT 1,
    executive_summary TEXT,
    technical_summary TEXT,
    beginner_explanation TEXT,
    comparison_table JSONB,
    pros_cons JSONB,
    consensus TEXT,
    disagreements TEXT,
    open_questions JSONB,
    future_research TEXT,
    evidence_used JSONB,
    conflicts_addressed JSONB,
    key_findings JSONB,
    research_confidence FLOAT,
    methodology_notes TEXT,
    references JSONB,
    notebook_note_id INTEGER REFERENCES knowledge_notes(id) ON DELETE SET NULL,
    collection_id INTEGER REFERENCES knowledge_collections(id) ON DELETE SET NULL,
    export_formats JSONB,
    generated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Research Sessions Table

```sql
CREATE TABLE research_sessions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id) ON DELETE CASCADE,
    session_type VARCHAR(50) NOT NULL,
    goal TEXT,
    queries_executed JSONB,
    evidence_collected INTEGER DEFAULT 0,
    tasks_executed INTEGER DEFAULT 0,
    agent_actions JSONB,
    session_summary TEXT,
    next_steps TEXT,
    status VARCHAR(20) DEFAULT 'in_progress',
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Research Plans Table

```sql
CREATE TABLE research_plans (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES research_projects(id) ON DELETE CASCADE,
    research_goal TEXT NOT NULL,
    objectives JSONB,
    research_questions JSONB,
    subtasks JSONB,
    expected_sources JSONB,
    missing_information JSONB,
    estimated_complexity VARCHAR(20),
    estimated_duration_hours FLOAT,
    priority_order JSONB,
    execution_plan JSONB,
    is_approved BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Backend Services

### ResearchPlannerService

- Create research projects
- Generate research plans from goals
- Decompose tasks into subtasks
- Update task status and progress

### EvidenceService

- Add evidence from various sources
- Calculate authority, freshness, popularity scores
- Rank evidence by multi-factor algorithm
- Import from workspace documents

### ConflictDetectionService

- Detect conflicting claims
- Detect different definitions
- Detect date conflicts
- Detect metric conflicts
- Resolve or acknowledge conflicts

### SynthesisService

- Generate executive summaries
- Generate technical summaries
- Generate beginner explanations
- Generate comparison tables
- Identify consensus and disagreements

### ReportGenerationService

- Generate comprehensive reports
- Calculate research confidence
- Export as Markdown/HTML
- Integrate with notebook

---

## API Endpoints

### Project Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research/projects` | Create project |
| GET | `/research/projects` | List projects |
| GET | `/research/projects/{id}` | Get project |
| POST | `/research/projects/{id}/plan` | Generate plan |
| GET | `/research/projects/{id}/tasks` | Get tasks |

### Task Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research/tasks/{id}/decompose` | Decompose task |
| PUT | `/research/tasks/{id}/status` | Update status |

### Evidence Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research/evidence` | Add evidence |
| GET | `/research/projects/{id}/evidence` | Get evidence |
| GET | `/research/evidence/{id}/confidence` | Get confidence |

### Conflict Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research/projects/{id}/detect-conflicts` | Detect conflicts |
| GET | `/research/projects/{id}/conflicts` | Get conflicts |
| GET | `/research/projects/{id}/conflict-stats` | Get statistics |

### Report Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research/projects/{id}/reports` | Generate report |
| GET | `/research/projects/{id}/reports` | List reports |
| GET | `/research/reports/{id}` | Get report |
| GET | `/research/reports/{id}/export/markdown` | Export MD |
| GET | `/research/reports/{id}/export/html` | Export HTML |

---

## Evidence Ranking Algorithm

```
Overall Score = (
    Relevance × 0.30 +
    Credibility × 0.25 +
    Authority × 0.20 +
    Freshness × 0.15 +
    Popularity × 0.10
)
```

### Source Types & Authority

| Source | Authority Score |
|--------|----------------|
| Workspace | 0.95 |
| Documentation | 0.85 |
| ArXiv/DOI | 0.90 |
| GitHub | 0.70 |
| Web Page | 0.50 |
| Blog | 0.40 |
| Video | 0.50 |

---

## Conflict Types

| Type | Description |
|------|-------------|
| claim | Conflicting factual claims |
| definition | Different definitions |
| date | Different dates for same event |
| metric | Different statistics/metrics |
| conclusion | Different conclusions |

---

## Report Types

| Type | Description |
|------|-------------|
| comprehensive | Full research report |
| executive | Brief executive summary |
| technical | Detailed technical analysis |

---

## Live Workflow Events

```
research.planning          - Planning research
research.task_breakdown   - Breaking into tasks
research.gathering        - Collecting evidence
research.verifying        - Verifying sources
research.ranking          - Ranking evidence
research.conflict_check    - Checking conflicts
research.synthesizing     - Synthesizing knowledge
research.reporting         - Generating report
research.completed         - Research complete
```

---

## Future Integration Points

### Phase 6: Knowledge Graph
- Consume: Research relationships
- Generate: Interactive visualizations

### Phase 7: Exam Engine
- Consume: Research reports
- Generate: Exam questions

### Phase 8: Job Hunter
- Consume: Research findings
- Generate: Job matches

### Phase 9: Multi-Agent
- Consume: All research data
- Generate: Coordinated research

### Phase 10: Analytics
- Consume: Research metrics
- Generate: Research analytics

---

## Files Added

```
backend/src/research/models.py
backend/src/research/__init__.py
backend/src/research/planner_service.py
backend/src/research/evidence_service.py
backend/src/research/conflict_service.py
backend/src/research/synthesis_service.py
backend/src/research/report_service.py
backend/src/api/research.py
docs/architecture/phase-5-research-operating-system.md
```

---

## Git Commit Summary

```
Phase 5: Research Operating System (ResearchOS)

## Database Models (6 tables)
- research_projects: Research organization
- research_tasks: Task decomposition
- research_evidence: Evidence collection
- research_conflicts: Conflict detection
- research_reports: Report generation
- research_sessions: Session tracking
- research_plans: Research planning

## Backend Services (5 services)
- ResearchPlannerService: Project & plan management
- EvidenceService: Evidence collection & ranking
- ConflictDetectionService: Conflict detection
- SynthesisService: Knowledge synthesis
- ReportGenerationService: Report generation

## API Endpoints (20+ endpoints)
- /research/projects - Project CRUD
- /research/tasks - Task management
- /research/evidence - Evidence management
- /research/conflicts - Conflict detection
- /research/reports - Report generation
- /research/synthesis - Knowledge synthesis

## Key Features
- Research planning from goals
- Multi-source evidence collection
- Authority & credibility scoring
- Evidence ranking algorithm
- Conflict detection
- Knowledge synthesis
- Report generation (MD/HTML)
- Notebook integration
```
