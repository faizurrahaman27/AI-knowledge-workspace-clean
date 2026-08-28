# Phase 3: Knowledge Intelligence Engine

## Architecture Documentation

**Date:** 2026-07-19  
**Phase:** 3 - Knowledge Intelligence Engine  
**Status:** Complete

---

## Executive Summary

Phase 3 introduces the Knowledge Intelligence Engine - the AI brain of the platform that transforms every uploaded document into structured, reusable knowledge. This knowledge becomes the foundation for all future subsystems including NotebookLM, Deep Research, Knowledge Graph, Exam Engine, Job Hunter, and Analytics.

### Key Features

- **Modular extraction services** for each knowledge type
- **Multi-level summaries** (one-sentence, executive, bullet, detailed)
- **Entity extraction** with 15+ entity types
- **Concept extraction** independent of named entities
- **Relationship extraction** for knowledge graph generation
- **Question generation** at 3 difficulty levels
- **Flashcard generation** for spaced repetition
- **Topic classification** with hierarchies
- **Semantic tagging** across 9 tag categories
- **Real-time progress** via WebSocket events

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Knowledge Intelligence Pipeline                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐           │
│  │   Document   │───►│    Text       │───►│   Metadata    │           │
│  │   Upload     │    │   Extraction  │    │   Extractor  │           │
│  └───────────────┘    └───────────────┘    └───────┬───────┘           │
│                                                      │                   │
│                                                      ▼                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     LLM-Based Extraction                          │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │   │
│  │  │   Summary   │ │   Entity    │ │  Concept    │               │   │
│  │  │  Service   │ │  Service    │ │  Service    │               │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘               │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │   │
│  │  │ Relationship│ │  Question   │ │  Flashcard  │               │   │
│  │  │  Service   │ │  Generator  │ │  Generator  │               │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘               │   │
│  │  ┌─────────────┐ ┌─────────────┐                               │   │
│  │  │   Topic     │ │   Semantic   │                               │   │
│  │  │  Classifier │ │   Tagger     │                               │   │
│  │  └─────────────┘ └─────────────┘                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Structured Database Storage                    │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │   │
│  │  │Summary  │ │ Entities│ │ Concepts│ │Relations│              │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘              │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │   │
│  │  │Questions│ │Flashcards│ │ Topics │ │  Tags  │              │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### New Tables

#### document_summaries
```sql
CREATE TABLE document_summaries (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    one_sentence_summary TEXT,
    executive_summary TEXT,
    bullet_summary TEXT,
    detailed_summary TEXT,
    chapter_summary JSONB,
    version INTEGER DEFAULT 1,
    confidence_score FLOAT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id)
);
```

#### knowledge_entities
```sql
CREATE TABLE knowledge_entities (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    canonical_name VARCHAR(500),
    description TEXT,
    mentions INTEGER DEFAULT 1,
    first_mention TEXT,
    aliases JSONB,
    page_number INTEGER,
    section_title VARCHAR(500),
    confidence_score FLOAT,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_entities_document ON knowledge_entities(document_id);
CREATE INDEX ix_entities_type ON knowledge_entities(entity_type);
CREATE INDEX ix_entities_name ON knowledge_entities(name);
```

#### knowledge_concepts
```sql
CREATE TABLE knowledge_concepts (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    importance VARCHAR(20),
    difficulty VARCHAR(20),
    related_concepts JSONB,
    related_entities JSONB,
    first_definition TEXT,
    usage_examples JSONB,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_concepts_document ON knowledge_concepts(document_id);
CREATE INDEX ix_concepts_name ON knowledge_concepts(name);
```

#### knowledge_relationships
```sql
CREATE TABLE knowledge_relationships (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL,
    source_id INTEGER NOT NULL,
    source_name VARCHAR(500) NOT NULL,
    relationship_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(20) NOT NULL,
    target_id INTEGER NOT NULL,
    target_name VARCHAR(500) NOT NULL,
    description TEXT,
    evidence TEXT,
    page_number INTEGER,
    confidence_score FLOAT,
    is_inferred BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_relationships_document ON knowledge_relationships(document_id);
CREATE INDEX ix_relationships_source ON knowledge_relationships(source_type, source_id);
CREATE INDEX ix_relationships_target ON knowledge_relationships(target_type, target_id);
```

#### generated_questions
```sql
CREATE TABLE generated_questions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    answer TEXT,
    options JSONB,
    correct_option_index INTEGER,
    topic VARCHAR(500),
    related_concept VARCHAR(500),
    related_entity_id INTEGER,
    confidence_score FLOAT,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_questions_document ON generated_questions(document_id);
CREATE INDEX ix_questions_type ON generated_questions(question_type);
CREATE INDEX ix_questions_difficulty ON generated_questions(difficulty);
```

#### knowledge_flashcards
```sql
CREATE TABLE knowledge_flashcards (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    topic VARCHAR(500),
    tags JSONB,
    difficulty VARCHAR(20) NOT NULL,
    source_reference TEXT,
    related_concept VARCHAR(500),
    confidence_score FLOAT,
    ease_factor FLOAT DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    next_review TIMESTAMP,
    last_reviewed TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_flashcards_document ON knowledge_flashcards(document_id);
CREATE INDEX ix_flashcards_topic ON knowledge_flashcards(topic);
CREATE INDEX ix_flashcards_next_review ON knowledge_flashcards(next_review);
```

#### document_topics
```sql
CREATE TABLE document_topics (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    topic_name VARCHAR(500) NOT NULL,
    topic_type VARCHAR(50),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    hierarchy_path JSONB,
    prerequisite_topics JSONB,
    related_topics JSONB,
    confidence_score FLOAT,
    importance_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_topics_document ON document_topics(document_id);
CREATE INDEX ix_topics_name ON document_topics(topic_name);
CREATE INDEX ix_topics_category ON document_topics(category);
```

#### semantic_tags
```sql
CREATE TABLE semantic_tags (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    tag VARCHAR(200) NOT NULL,
    tag_category VARCHAR(50) NOT NULL,
    context TEXT,
    relevance_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id, tag, tag_category)
);
CREATE INDEX ix_tags_document ON semantic_tags(document_id);
CREATE INDEX ix_tags_category ON semantic_tags(tag_category);
CREATE INDEX ix_tags_tag ON semantic_tags(tag);
```

#### document_sections
```sql
CREATE TABLE document_sections (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    title VARCHAR(500),
    level INTEGER DEFAULT 1,
    start_page INTEGER,
    end_page INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    summary TEXT,
    key_points JSONB,
    estimated_reading_time_minutes FLOAT,
    order_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_sections_document ON document_sections(document_id);
CREATE INDEX ix_sections_order ON document_sections(document_id, order_index);
```

#### knowledge_metadata
```sql
CREATE TABLE knowledge_metadata (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    language VARCHAR(10),
    language_name VARCHAR(50),
    document_category VARCHAR(100),
    academic_subject VARCHAR(200),
    industry_tags JSONB,
    quality_score FLOAT,
    completeness_score FLOAT,
    reading_time_minutes FLOAT,
    difficulty_score FLOAT,
    processing_version VARCHAR(50),
    models_used JSONB,
    processing_duration_ms INTEGER,
    entity_count INTEGER DEFAULT 0,
    concept_count INTEGER DEFAULT 0,
    relationship_count INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0,
    flashcard_count INTEGER DEFAULT 0,
    section_count INTEGER DEFAULT 0,
    extraction_complete BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id)
);
```

### Updated Tables

#### documents
```sql
ALTER TABLE documents ADD COLUMN knowledge_extracted INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN extraction_error VARCHAR;
```

---

## Processing Pipeline

### Stage Breakdown

| Stage | Service | Weight | Estimated Time |
|-------|---------|--------|----------------|
| 1 | Metadata Extraction | 5% | 3s |
| 2 | Topic Classification | 8% | 12s |
| 3 | Summary Generation | 12% | 20s |
| 4 | Entity Extraction | 15% | 15s |
| 5 | Concept Extraction | 15% | 15s |
| 6 | Relationship Extraction | 15% | 20s |
| 7 | Question Generation | 10% | 25s |
| 8 | Flashcard Generation | 10% | 20s |
| 9 | Semantic Tagging | 10% | 10s |

### WebSocket Events

The pipeline emits the following events:

```
knowledge.extraction.started       - Extraction began
knowledge.extraction.stage         - Stage progress update
knowledge.extraction.entity        - Entity extracted
knowledge.extraction.concept       - Concept extracted
knowledge.extraction.completed     - Extraction finished
knowledge.extraction.failed        - Extraction failed
```

---

## API Documentation

### Knowledge Retrieval Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/knowledge/{document_id}/summary` | Get all summary levels |
| GET | `/knowledge/{document_id}/entities` | Get extracted entities |
| GET | `/knowledge/{document_id}/concepts` | Get extracted concepts |
| GET | `/knowledge/{document_id}/relationships` | Get relationships |
| GET | `/knowledge/{document_id}/questions` | Get generated questions |
| GET | `/knowledge/{document_id}/flashcards` | Get generated flashcards |
| GET | `/knowledge/{document_id}/topics` | Get classified topics |
| GET | `/knowledge/{document_id}/tags` | Get semantic tags |
| GET | `/knowledge/{document_id}/metadata` | Get extraction metadata |

### Knowledge Extraction Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/knowledge/{document_id}/extract` | Trigger extraction |
| GET | `/knowledge/{document_id}/extraction-status` | Get extraction status |

### Search Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/knowledge/search/concepts` | Search concepts across documents |
| GET | `/knowledge/search/entities` | Search entities across documents |

---

## Service Interfaces

### BaseExtractionService

```python
class BaseExtractionService(ABC):
    service_name: str
    estimated_time_ms: int
    
    def extract(self, context: ExtractionContext) -> ExtractionResult:
        """Main extraction method"""
        
    @abstractmethod
    def _extract(self, context: ExtractionContext) -> Any:
        """Implementation of extraction logic"""
```

### ExtractionContext

```python
@dataclass
class ExtractionContext:
    document_id: int
    text: str
    language_code: Optional[str]
    metadata: Optional[Dict]
    progress_callback: Optional[Callable]
```

### ExtractionResult

```python
@dataclass
class ExtractionResult:
    success: bool
    data: Optional[Any]
    error: Optional[str]
    confidence_score: Optional[float]
    processing_time_ms: Optional[int]
    metadata: Optional[Dict]
```

---

## Entity Types

The system supports the following entity types:

| Type | Description |
|------|-------------|
| person | Named individuals |
| organization | Organizations and groups |
| company | Companies and businesses |
| technology | Technologies and techniques |
| programming_language | Programming languages |
| framework | Software frameworks |
| model | AI/ML models |
| dataset | Datasets |
| library | Software libraries |
| tool | Tools and utilities |
| website | Websites and URLs |
| research_paper | Academic papers |
| book | Books and publications |
| institution | Institutions |
| product | Products |
| event | Events |
| location | Geographic locations |
| other | Miscellaneous |

---

## Relationship Types

| Type | Description |
|------|-------------|
| uses | X uses Y |
| implements | X implements Y |
| depends_on | X depends on Y |
| requires | X requires Y |
| enables | X enables Y |
| extends | X extends Y |
| composed_of | X is composed of Y |
| part_of | X is part of Y |
| related_to | X is related to Y |
| defined_in | X is defined in Y |
| introduced_by | X was introduced by Y |
| authored_by | X was authored by Y |
| published_in | X was published in Y |

---

## Tag Categories

| Category | Description |
|----------|-------------|
| skill | Skills and competencies |
| technology | Technologies |
| industry | Industry classifications |
| academic_domain | Academic fields |
| programming_language | Programming languages |
| library | Software libraries |
| framework | Software frameworks |
| research_area | Research areas |
| career_domain | Career-related topics |

---

## Design Decisions

### 1. Modular Service Architecture

Each extraction service is independent and can be:
- Replaced with alternative implementations
- Disabled without affecting other services
- Extended with new capabilities

### 2. LLM-Based Extraction

All complex extraction (entities, concepts, relationships, etc.) uses LLMs for:
- High accuracy entity recognition
- Contextual understanding
- Consistent output format

### 3. Extensible Design

New entity types, relationship types, and tag categories can be added without modifying existing code.

### 4. Progress Reporting

Every stage emits progress events for real-time UI updates.

### 5. Confidence Scoring

All extracted data includes confidence scores for quality assessment.

---

## Known Limitations

1. **LLM Dependency**: All extraction services require an LLM provider
2. **Processing Time**: Full extraction takes 2-3 minutes per document
3. **Text Length**: Very long documents may need chunking
4. **Language Support**: Optimized for English; other languages may have reduced accuracy
5. **No Streaming**: Extraction must complete before results are available

---

## Future Integration Points

### Phase 4: NotebookLM Features
- Consume: Summaries, topics, flashcards
- Generate: Reading guides, study notes

### Phase 5: Deep Research
- Consume: All extracted knowledge
- Generate: Research reports, literature reviews

### Phase 6: Knowledge Graph
- Consume: Entities, concepts, relationships
- Generate: Graph visualizations

### Phase 7: Exam Engine
- Consume: Questions, flashcards, topics
- Generate: Quizzes, assessments

### Phase 8: Job Hunter
- Consume: Skills, technologies, topics
- Generate: Resume matches, job recommendations

### Phase 9: Multi-Agent System
- Consume: All structured knowledge
- Enable: Cross-document reasoning

### Phase 10: Analytics
- Consume: Metadata, extraction statistics
- Generate: Learning analytics, progress tracking

---

## Performance Considerations

1. **Parallel Processing**: Services can run in parallel (future enhancement)
2. **Caching**: Extracted knowledge is cached in database
3. **Incremental Extraction**: Only new/modified documents need reprocessing
4. **Batch Processing**: Multiple documents can be queued

---

## Testing

### Unit Tests
- Each service has isolated unit tests
- Mock LLM responses for deterministic testing

### Integration Tests
- Full pipeline tests with real documents
- Database persistence validation

### E2E Tests
- Document upload → Knowledge extraction → API retrieval

---

## Git Commit Summary

```
Phase 3: Knowledge Intelligence Engine

- Created knowledge module with 9 extraction services
- Implemented structured database models for all knowledge types
- Created knowledge processing pipeline with progress reporting
- Added comprehensive API endpoints for knowledge retrieval
- Created frontend KnowledgePanel component
- Added WebSocket events for extraction progress
- Maintained backward compatibility with existing functionality
```

---

## Files Added

```
backend/src/knowledge/__init__.py
backend/src/knowledge/models.py
backend/src/knowledge/extraction/__init__.py
backend/src/knowledge/extraction/base.py
backend/src/knowledge/extraction/summarizer.py
backend/src/knowledge/extraction/entity_extractor.py
backend/src/knowledge/extraction/concept_extractor.py
backend/src/knowledge/extraction/relationship_extractor.py
backend/src/knowledge/extraction/question_generator.py
backend/src/knowledge/extraction/flashcard_generator.py
backend/src/knowledge/extraction/topic_classifier.py
backend/src/knowledge/extraction/semantic_tagger.py
backend/src/knowledge/extraction/metadata_extractor.py
backend/src/knowledge/processing/__init__.py
backend/src/knowledge/processing/pipeline.py
backend/src/api/knowledge.py
backend/src/models/document.py (updated)
frontend/src/components/KnowledgePanel.jsx
docs/architecture/phase-3-knowledge-intelligence.md
```
