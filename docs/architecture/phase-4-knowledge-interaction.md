# Phase 4: Knowledge Interaction Layer

## Architecture Documentation

**Date:** 2026-07-19  
**Phase:** 4 - Knowledge Interaction Layer  
**Status:** Complete

---

## Executive Summary

Phase 4 transforms the AI Knowledge Workspace into an interactive platform where users can chat, research, write, annotate, explore, compare, and connect using validated knowledge. This layer becomes the primary user interface for all future capabilities.

### Key Features

- **AI Notebook**: Intelligent note-taking with knowledge citations
- **Collections**: Organize documents, notes, flashcards, questions
- **Knowledge Explorer**: Browse topics, concepts, entities, relationships
- **Semantic Search**: Unified search across all knowledge types
- **Activity Tracking**: Dashboard, recent items, pins, bookmarks
- **Live Workflow**: Real-time progress via WebSocket

---

## Workspace Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI Knowledge Workspace                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────────────────────┐  ┌─────────────────────┐  │
│  │   LEFT     │  │         CENTER             │  │       RIGHT         │  │
│  │  SIDEBAR   │  │   AI NOTEBOOK             │  │   CONTEXT PANEL     │  │
│  │            │  │                            │  │                     │  │
│  │ • Explorer │  │ • Notes                    │  │ • Citations         │  │
│  │ • Recent   │  │ • Chat History            │  │ • Confidence        │  │
│  │ • Favorites│  │ • Knowledge Links         │  │ • Quality           │  │
│  │ • Tags     │  │ • Markdown/LaTeX          │  │ • Provenance        │  │
│  │ • Collections│ │ • Pinned Responses        │  │ • Related Knowledge │  │
│  └─────────────┘  └─────────────────────────────┘  └─────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     LIVE WORKFLOW MONITOR                               │  │
│  │  Searching Workspace → Finding Concepts → Matching Citations → Building  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### New Tables

#### knowledge_notes
```sql
CREATE TABLE knowledge_notes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500),
    content TEXT NOT NULL,
    note_type VARCHAR(50) DEFAULT 'user',
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    source_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    source_concept_id INTEGER,
    source_question_id INTEGER REFERENCES generated_questions(id) ON DELETE SET NULL,
    source_flashcard_id INTEGER REFERENCES knowledge_flashcards(id) ON DELETE SET NULL,
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_model VARCHAR(100),
    ai_provider VARCHAR(100),
    citations JSONB,
    format_type VARCHAR(20) DEFAULT 'markdown',
    is_pinned BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_notes_user ON knowledge_notes(user_id);
CREATE INDEX ix_notes_workspace ON knowledge_notes(workspace_id);
```

#### knowledge_collections
```sql
CREATE TABLE knowledge_collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    collection_type VARCHAR(50) DEFAULT 'folder',
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES knowledge_collections(id) ON DELETE CASCADE,
    color VARCHAR(20),
    icon VARCHAR(50),
    tags JSONB,
    is_public BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_collections_user ON knowledge_collections(user_id);
CREATE INDEX ix_collections_parent ON knowledge_collections(parent_id);
```

#### collection_items
```sql
CREATE TABLE collection_items (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER REFERENCES knowledge_collections(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL,
    item_id INTEGER NOT NULL,
    order_index INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(collection_id, item_type, item_id)
);
CREATE INDEX ix_collection_items_collection ON collection_items(collection_id);
```

#### knowledge_bookmarks
```sql
CREATE TABLE knowledge_bookmarks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL,
    item_id INTEGER NOT NULL,
    title VARCHAR(500),
    notes TEXT,
    position INTEGER,
    collection_id INTEGER REFERENCES knowledge_collections(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_bookmarks_user ON knowledge_bookmarks(user_id);
```

#### pinned_items
```sql
CREATE TABLE pinned_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL,
    item_id INTEGER NOT NULL,
    pin_type VARCHAR(50) DEFAULT 'pin',
    title VARCHAR(500),
    thumbnail VARCHAR(500),
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, item_type, item_id)
);
CREATE INDEX ix_pinned_user ON pinned_items(user_id);
```

#### recent_activity
```sql
CREATE TABLE recent_activity (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    item_id INTEGER NOT NULL,
    title VARCHAR(500),
    preview TEXT,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_recent_user ON recent_activity(user_id);
CREATE INDEX ix_recent_created ON recent_activity(created_at);
```

#### workspace_layouts
```sql
CREATE TABLE workspace_layouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE,
    layout_name VARCHAR(100) DEFAULT 'default',
    layout_config JSONB NOT NULL,
    panel_states JSONB,
    active_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    active_note_id INTEGER REFERENCES knowledge_notes(id) ON DELETE SET NULL,
    theme VARCHAR(20) DEFAULT 'dark',
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, workspace_id)
);
```

---

## Backend Services

### NotebookService

Manages AI Notebook notes:
- Create, update, delete notes
- Pin/unpin notes
- Search notes
- Convert AI responses to notes

### CollectionService

Manages user collections:
- Create, update, delete collections
- Add/remove items from collections
- Collection tree structure
- Toggle favorites

### KnowledgeExplorerService

Provides knowledge exploration:
- Topics overview
- Entity browsing by type
- Relationship overview
- Related knowledge
- Knowledge graph preview
- Dashboard statistics

### SemanticSearchService

Unified search across knowledge:
- Search documents, concepts, entities, notes, questions, flashcards, topics
- Unified search results
- Search suggestions
- Search by tag

### RecentActivityService

Tracks user activity:
- Log activities
- Get recent activity
- Dashboard data
- Pinned items
- Bookmarks

---

## API Endpoints

### Notebook Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/knowledge/interaction/notes` | Create note |
| GET | `/knowledge/interaction/notes` | Get notes |
| GET | `/knowledge/interaction/notes/{id}` | Get note |
| PUT | `/knowledge/interaction/notes/{id}` | Update note |
| DELETE | `/knowledge/interaction/notes/{id}` | Delete note |
| POST | `/knowledge/interaction/notes/{id}/pin` | Pin/unpin note |

### Collection Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/knowledge/interaction/collections` | Create collection |
| GET | `/knowledge/interaction/collections` | Get collections |
| GET | `/knowledge/interaction/collections/tree` | Get collection tree |
| POST | `/knowledge/interaction/collections/{id}/items` | Add item |
| GET | `/knowledge/interaction/collections/{id}/items` | Get items |
| DELETE | `/knowledge/interaction/collections/{id}/items/{type}/{id}` | Remove item |

### Explorer Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/knowledge/interaction/explorer/topics` | Get topics overview |
| GET | `/knowledge/interaction/explorer/entities` | Get entities by type |
| GET | `/knowledge/interaction/explorer/entity-types` | Get entity types |
| GET | `/knowledge/interaction/explorer/relationships` | Get relationships |
| GET | `/knowledge/interaction/explorer/related/{type}/{id}` | Get related knowledge |
| GET | `/knowledge/interaction/explorer/graph/{doc_id}` | Get knowledge graph |
| GET | `/knowledge/interaction/explorer/quality` | Get quality overview |
| GET | `/knowledge/interaction/explorer/stats` | Get dashboard stats |

### Search Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/knowledge/interaction/search` | Search knowledge |
| GET | `/knowledge/interaction/search/unified` | Unified search |
| GET | `/knowledge/interaction/search/suggestions` | Search suggestions |

### Activity Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/knowledge/interaction/activity/recent` | Get recent activity |
| GET | `/knowledge/interaction/activity/dashboard` | Get dashboard |
| GET | `/knowledge/interaction/activity/pins` | Get pinned items |
| POST | `/knowledge/interaction/activity/pins` | Pin item |
| DELETE | `/knowledge/interaction/activity/pins/{type}/{id}` | Unpin item |
| GET | `/knowledge/interaction/activity/summary` | Get activity summary |

---

## Frontend Components

### WorkspaceLayout

Main workspace container with all panels:
- Left sidebar (Explorer, Collections, Recent)
- Center panel (AI Notebook, Chat)
- Right sidebar (Context, Citations)
- Bottom panel (Live Workflow Monitor)

### NotebookPanel

AI Notebook interface:
- Note editor with Markdown/LaTeX support
- Pin responses
- Save as notes
- Knowledge citations

### KnowledgeExplorer

Knowledge browsing:
- Topics view
- Entities view
- Relationships view
- Related knowledge

### ContextSidebar

AI Context display:
- Citations
- Confidence scores
- Quality indicators
- Provenance
- Related knowledge

### SemanticSearchBar

Global search:
- Unified search across types
- Suggestions
- Filter by type

### CollectionPanel

Collection management:
- Tree view
- Add/remove items
- Favorites

### PinnedItemsPanel

Pinned items display:
- Notes
- Responses
- Documents

---

## Live Workflow Events

The system broadcasts workflow progress:

```
workflow.started          - Workflow started
workflow.searching        - Searching workspace
workflow.finding_concepts - Finding concepts
workflow.matching_citations - Matching citations
workflow.building_answer  - Building answer
workflow.calculating_confidence - Calculating confidence
workflow.ranking_sources  - Ranking sources
workflow.finalizing       - Finalizing response
workflow.completed        - Workflow completed
```

---

## Design Decisions

### 1. Knowledge-Centric Notes

Notes are linked to validated knowledge, not raw documents:
- Every note can have citations
- Notes derive from concepts, flashcards, questions
- AI responses can be saved as notes

### 2. Unified Search

Single search interface across all knowledge types:
- Documents, concepts, entities, notes, questions, flashcards, topics
- Results ranked by type priority
- Filter by specific types

### 3. Activity Tracking

Comprehensive activity tracking for dashboard:
- Opened, generated, studied, uploaded
- Recent items
- Pinned items
- Bookmarks

### 4. Collection Hierarchy

Nested collections for organization:
- Folder-like structure
- Multi-type items
- Favorites

---

## Known Limitations

1. **Vector Search**: Not implemented; uses keyword search
2. **Real-time Collaboration**: Not implemented
3. **Knowledge Graph Visualization**: Placeholder only
4. **Export**: Basic export not implemented

---

## Future Integration Points

### Phase 5: Deep Research
- Consume: Notebook notes, Search results
- Generate: Research reports

### Phase 6: Knowledge Graph
- Consume: Graph preview data
- Generate: Interactive visualizations

### Phase 7: Exam Engine
- Consume: Flashcards, Questions, Collections
- Generate: Quizzes, Assessments

### Phase 8: Job Hunter
- Consume: Entities (skills), Topics
- Generate: Job matches

### Phase 9: Multi-Agent
- Consume: All interaction data
- Generate: Coordinated responses

### Phase 10: Analytics
- Consume: Activity tracking
- Generate: Learning analytics

---

## Performance Considerations

1. **Search**: Uses database indexing for fast retrieval
2. **Activity**: Cleaned up automatically (max 100 per user)
3. **Collections**: Lazy-loaded tree structure
4. **Pagination**: All list endpoints support pagination

---

## Files Added

```
backend/src/knowledge/interaction_models.py
backend/src/knowledge/interaction/__init__.py
backend/src/knowledge/interaction/notebook_service.py
backend/src/knowledge/interaction/collection_service.py
backend/src/knowledge/interaction/explorer_service.py
backend/src/knowledge/interaction/search_service.py
backend/src/knowledge/interaction/activity_service.py
backend/src/api/interaction.py
docs/architecture/phase-4-knowledge-interaction.md
```

---

## Git Commit Summary

```
Phase 4: Knowledge Interaction Layer

## Backend
- Created 5 interaction services
- Added 40+ API endpoints
- Implemented Notebook, Collections, Explorer, Search, Activity

## Database
- Added 7 new tables for interaction data
- Normalized schema for collections, notes, activity

## Features
- AI Notebook with citations
- Knowledge Collections with hierarchy
- Knowledge Explorer
- Semantic Search
- Activity Tracking & Dashboard
- Pinned Items & Bookmarks

## Architecture
- Modular service design
- RESTful API
- Unified search
- Activity tracking

## Documentation
- Comprehensive architecture docs
- API reference
- Database schema
```
