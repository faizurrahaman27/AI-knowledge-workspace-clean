# Phase 3.5: Knowledge Validation & Quality Layer

## Architecture Documentation

**Date:** 2026-07-19  
**Phase:** 3.5 - Knowledge Validation & Quality Layer  
**Status:** Complete

---

## Executive Summary

Phase 3.5 introduces a comprehensive validation and quality layer that ensures all extracted knowledge is trustworthy, traceable, and reliable before becoming available to future subsystems.

### Key Features

- **10 modular validation services** for different validation aspects
- **Citation mapping** for full provenance tracking
- **Entity resolution** for duplicate detection
- **Quality scoring** with multi-dimensional metrics
- **Version tracking** for reprocessing support
- **Complete audit logging** for all operations
- **Confidence scoring** with breakdown by category

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Knowledge Validation Pipeline                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐               │
│  │   Document   │───►│  Extraction   │───►│   Citation   │               │
│  │   Upload     │    │   Engine      │    │   Mapping    │               │
│  └───────────────┘    └───────────────┘    └───────┬───────┘               │
│                                                      │                       │
│                                                      ▼                       │
│  ┌───────────────────────────────────────────────────────────────┐           │
│  │                     Validation Services                        │           │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │           │
│  │  │ Entity  │ │Duplicate│ │Canonical│ │Consist.│          │           │
│  │  │Resolver │ │Detector │ │ izer    │ │Validate │          │           │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │           │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │           │
│  │  │Confidence│ │ Quality │ │ Version │ │  Audit  │          │           │
│  │  │ Scoring │ │ Scoring │ │ Tracking│ │ Logging │          │           │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │           │
│  └───────────────────────────────────────────────────────────────┘           │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────┐           │
│  │                    Validated Knowledge                         │           │
│  │  • Confidence Scores  • Quality Scores  • Citations            │           │
│  │  • Version History  • Audit Trail  • Canonical Entities     │           │
│  └───────────────────────────────────────────────────────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Validation Pipeline

### Stage Breakdown

| Stage | Service | Weight | Purpose |
|-------|---------|--------|---------|
| 1 | Citation Mapping | 10% | Map knowledge to source locations |
| 2 | Entity Resolution | 15% | Resolve duplicate entities |
| 3 | Duplicate Detection | 15% | Detect and remove duplicates |
| 4 | Canonicalization | 10% | Standardize knowledge formats |
| 5 | Consistency Validation | 15% | Check internal consistency |
| 6 | Confidence Scoring | 15% | Calculate confidence scores |
| 7 | Quality Scoring | 15% | Calculate quality scores |
| 8 | Version Tracking | 5% | Record version history |

---

## Database Schema

### New Tables

#### knowledge_citations
```sql
CREATE TABLE knowledge_citations (
    id SERIAL PRIMARY KEY,
    knowledge_type VARCHAR(50) NOT NULL,
    knowledge_id INTEGER NOT NULL,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL,
    source_id VARCHAR(100),
    page_number INTEGER,
    section_title VARCHAR(500),
    text_excerpt TEXT,
    character_start INTEGER,
    character_end INTEGER,
    relevance_score FLOAT,
    is_primary BOOLEAN DEFAULT FALSE,
    provenance_chain JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_citations_knowledge ON knowledge_citations(knowledge_type, knowledge_id);
CREATE INDEX ix_citations_document ON knowledge_citations(document_id);
```

#### validation_records
```sql
CREATE TABLE validation_records (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    validation_type VARCHAR(50) NOT NULL,
    knowledge_type VARCHAR(50),
    knowledge_id INTEGER,
    status VARCHAR(20) NOT NULL,
    passed BOOLEAN NOT NULL,
    message TEXT,
    error_code VARCHAR(50),
    details JSONB,
    remediation_action VARCHAR(100),
    remediation_applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_validation_document ON validation_records(document_id);
CREATE INDEX ix_validation_type ON validation_records(validation_type);
```

#### canonical_entities
```sql
CREATE TABLE canonical_entities (
    id SERIAL PRIMARY KEY,
    canonical_name VARCHAR(500) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    aliases JSONB,
    merged_entity_ids JSONB,
    occurrence_count INTEGER DEFAULT 0,
    document_count INTEGER DEFAULT 0,
    canonical_description TEXT,
    first_seen TIMESTAMP,
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(canonical_name, entity_type)
);
CREATE INDEX ix_canonical_name ON canonical_entities(canonical_name);
CREATE INDEX ix_canonical_type ON canonical_entities(entity_type);
```

#### knowledge_versions
```sql
CREATE TABLE knowledge_versions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    is_current BOOLEAN DEFAULT TRUE,
    extraction_version VARCHAR(50),
    prompt_version VARCHAR(50),
    llm_provider VARCHAR(100),
    llm_model VARCHAR(100),
    embedding_model VARCHAR(100),
    processing_strategy VARCHAR(100),
    processing_duration_ms INTEGER,
    quality_score FLOAT,
    confidence_score FLOAT,
    extraction_timestamp TIMESTAMP,
    validation_timestamp TIMESTAMP,
    changelog TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_version_document ON knowledge_versions(document_id);
CREATE INDEX ix_version_current ON knowledge_versions(document_id, is_current);
```

#### knowledge_audit
```sql
CREATE TABLE knowledge_audit (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    knowledge_type VARCHAR(50),
    knowledge_id INTEGER,
    description TEXT NOT NULL,
    actor_type VARCHAR(20),
    actor_id VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    previous_value JSONB,
    new_value JSONB,
    service_name VARCHAR(100),
    processing_duration_ms INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_audit_document ON knowledge_audit(document_id);
CREATE INDEX ix_audit_event_type ON knowledge_audit(event_type);
CREATE INDEX ix_audit_created ON knowledge_audit(created_at);
CREATE INDEX ix_audit_knowledge ON knowledge_audit(knowledge_type, knowledge_id);
```

#### knowledge_quality
```sql
CREATE TABLE knowledge_quality (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE UNIQUE,
    overall_quality_score FLOAT,
    overall_confidence_score FLOAT,
    extraction_completeness FLOAT,
    entity_quality FLOAT,
    relationship_quality FLOAT,
    summary_quality FLOAT,
    citation_coverage FLOAT,
    topic_coverage FLOAT,
    metadata_completeness FLOAT,
    knowledge_density FLOAT,
    total_entities INTEGER DEFAULT 0,
    total_concepts INTEGER DEFAULT 0,
    total_relationships INTEGER DEFAULT 0,
    total_citations INTEGER DEFAULT 0,
    validated_count INTEGER DEFAULT 0,
    duplicate_count INTEGER DEFAULT 0,
    validation_passed INTEGER DEFAULT 0,
    validation_warnings INTEGER DEFAULT 0,
    validation_errors INTEGER DEFAULT 0,
    calculated_at TIMESTAMP DEFAULT NOW(),
    version_id INTEGER REFERENCES knowledge_versions(id)
);
CREATE INDEX ix_quality_document ON knowledge_quality(document_id);
CREATE INDEX ix_quality_score ON knowledge_quality(overall_quality_score);
```

---

## Service Interfaces

### Validation Services

| Service | Purpose | Key Methods |
|--------|---------|------------|
| CitationMappingService | Map knowledge to sources | create_citations, get_citations_for_knowledge |
| ConfidenceScoringService | Calculate confidence scores | calculate_confidence, calculate_document_confidence |
| EntityResolutionService | Resolve duplicate entities | resolve_entity, merge_entities |
| DuplicateDetectionService | Detect duplicates | find_duplicates, select_best_item |
| CanonicalizationService | Standardize formats | canonicalize_entity, canonicalize_concept |
| ConsistencyValidationService | Check consistency | validate_document |
| QualityScoringService | Calculate quality scores | calculate_quality, get_quality_for_document |
| KnowledgeVersionService | Track versions | create_version, get_version_history |
| AuditService | Log all operations | log_event, get_audit_history |

---

## API Endpoints

### Validation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/knowledge/{id}/validation` | Get validation results |
| GET | `/knowledge/{id}/quality` | Get quality scores |
| GET | `/knowledge/{id}/confidence` | Get confidence scores |
| GET | `/knowledge/{id}/citations` | Get knowledge citations |
| GET | `/knowledge/{id}/versions` | Get version history |
| GET | `/knowledge/{id}/audit` | Get audit trail |
| GET | `/knowledge/search/citations` | Search citations |

---

## Citation Mapping

### Provenance Chain

Every piece of knowledge maintains a provenance chain:

```
Flashcard
    ↓ Generated From
Concept
    ↓ Summary
Chunk (Page 5, Paragraph 2)
    ↓ Document
Original PDF
```

### Citation Structure

```json
{
  "id": 1,
  "knowledge_type": "entity",
  "knowledge_id": 42,
  "document_id": 10,
  "source_type": "chunk",
  "source_id": "chunk_5",
  "page_number": 5,
  "paragraph_index": 2,
  "text_excerpt": "...mentioned neural networks...",
  "relevance_score": 0.85,
  "is_primary": true,
  "provenance_chain": [
    {"type": "document", "id": 10, "description": "ML_Paper.pdf"},
    {"type": "page", "id": 5, "description": "Page 5"},
    {"type": "chunk", "id": "chunk_5", "description": "Neural Network Section"}
  ]
}
```

---

## Entity Resolution

### Normalization Rules

1. **Text Normalization**
   - Lowercase conversion
   - Whitespace standardization
   - Punctuation removal

2. **Name Variations**
   - "Open AI" → "openai"
   - "Open-AI" → "openai"
   - "OpenAI Inc." → "openai"

3. **Fuzzy Matching**
   - Similarity threshold: 85%
   - Uses SequenceMatcher for comparison

### Resolution Flow

```
Input: "Open AI"
    ↓
Normalize: "open ai"
    ↓
Search canonical entities
    ↓
Found: CanonicalEntity(canonical_name="openai")
    ↓
Update: Add alias, increment occurrence_count
    ↓
Return: canonical_id
```

---

## Confidence Scoring

### Multi-Dimensional Scoring

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Extraction | 30% | Based on LLM confidence |
| Consistency | 25% | Internal coherence |
| Citation | 25% | Source coverage |
| Semantic | 20% | Content validity |

### Example Output

```json
{
  "overall": 0.82,
  "extraction": 0.85,
  "consistency": 0.90,
  "citation": 0.75,
  "semantic": 0.78,
  "sources": {
    "extraction": 0.85,
    "consistency": 0.90,
    "citation": 0.75,
    "semantic": 0.78
  }
}
```

---

## Audit Log

### Event Types

| Event | Description |
|-------|-------------|
| EXTRACTION_STARTED | Extraction began |
| EXTRACTION_COMPLETED | Extraction finished |
| VALIDATION_STARTED | Validation began |
| VALIDATION_COMPLETED | Validation finished |
| ENTITY_MERGED | Entities were merged |
| DUPLICATE_REMOVED | Duplicates removed |
| CITATION_CREATED | Citation generated |
| QUALITY_SCORE_CALCULATED | Quality calculated |
| CONFIDENCE_CALCULATED | Confidence calculated |
| VERSION_UPDATED | Version recorded |

### Example Audit Entry

```json
{
  "id": 1,
  "event_type": "VALIDATION_COMPLETED",
  "document_id": 10,
  "description": "Validation completed for document 10",
  "actor_type": "system",
  "action": "update",
  "metadata": {
    "total_results": 15,
    "passed": 14,
    "failed": 1,
    "quality_score": 0.85,
    "confidence_score": 0.82
  },
  "created_at": "2026-07-19T10:00:00Z"
}
```

---

## Version Tracking

### Version Record

```json
{
  "id": 1,
  "document_id": 10,
  "version_number": 1,
  "is_current": true,
  "extraction_version": "1.0.0",
  "llm_provider": "groq",
  "llm_model": "llama-3.1-70b-versatile",
  "quality_score": 0.85,
  "confidence_score": 0.82,
  "extraction_timestamp": "2026-07-19T10:00:00Z",
  "processing_duration_ms": 45000
}
```

---

## Design Decisions

### 1. Separation of Concerns

Each validation service is independent and can be:
- Replaced with alternative implementations
- Disabled without affecting other services
- Extended with new capabilities

### 2. Audit-First Architecture

Every operation generates an audit record, ensuring:
- Complete traceability
- Debug capability
- Compliance support
- Historical analysis

### 3. Citation-Centric Design

All knowledge maintains citation references, enabling:
- Source verification
- Explainability
- Trustworthiness
- Reproducibility

### 4. Confidence vs Quality

Two distinct metrics:
- **Confidence**: How sure we are about extraction
- **Quality**: How good the knowledge is

---

## Known Limitations

1. **Entity Resolution**: Fuzzy matching can produce false positives
2. **Semantic Duplicates**: Text similarity may miss semantic duplicates
3. **Circular Relationships**: Detection can be expensive for large graphs
4. **Version Rollback**: Only metadata is updated; actual data rollback not implemented

---

## Future Integration Points

### Phase 4: NotebookLM
- Consume: Citations, Quality Scores
- Use: Audit trail for explanations

### Phase 5: Deep Research
- Consume: Provenance chains, Confidence scores
- Use: Source verification

### Phase 6: Knowledge Graph
- Consume: Canonical entities, Relationships
- Use: Citation mapping

### Phase 7: Exam Engine
- Consume: Quality scores, Confidence
- Use: Question reliability filtering

### Phase 8: Job Hunter
- Consume: Canonical entities, Entity resolution
- Use: Skill deduplication

### Phase 9: Multi-Agent
- Consume: All validated knowledge
- Use: Audit trail for reasoning

### Phase 10: Analytics
- Consume: Quality metrics, Audit logs
- Generate: Quality dashboards

---

## Performance Considerations

1. **Parallel Processing**: Services can run in parallel
2. **Batch Processing**: Multiple documents can be validated
3. **Caching**: Results cached in database
4. **Incremental**: Only new/modified knowledge validated

---

## Files Added

```
backend/src/knowledge/validation/__init__.py
backend/src/knowledge/validation/base.py
backend/src/knowledge/validation/citation_service.py
backend/src/knowledge/validation/confidence_service.py
backend/src/knowledge/validation/entity_resolver.py
backend/src/knowledge/validation/duplicate_detector.py
backend/src/knowledge/validation/canonicalizer.py
backend/src/knowledge/validation/consistency_service.py
backend/src/knowledge/validation/quality_service.py
backend/src/knowledge/validation/version_service.py
backend/src/knowledge/validation/audit_service.py
backend/src/knowledge/validation/pipeline.py
backend/src/knowledge/validation_models.py
docs/architecture/phase-3.5-knowledge-validation.md
```

---

## Git Commit Summary

```
Phase 3.5: Knowledge Validation & Quality Layer

- Created 9 validation services
- Implemented citation mapping for full provenance
- Added entity resolution with normalization
- Created duplicate detection for all knowledge types
- Implemented quality scoring with multi-dimensional metrics
- Added version tracking for reprocessing support
- Created comprehensive audit logging
- Maintained backward compatibility
```
