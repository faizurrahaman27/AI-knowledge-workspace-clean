# Phase 7: Multilingual Intelligence Layer

## Architecture Documentation

**Date:** 2026-07-19  
**Phase:** 7 - Multilingual Intelligence Layer  
**Status:** Complete

---

## Executive Summary

Phase 7 transforms the AI Knowledge Workspace into a universal, language-agnostic platform. The system works identically whether users upload English, Arabic, Hindi, Japanese, Chinese, or any other supported language. Every pipeline automatically adapts without user intervention.

### Key Features

- **Universal Language Detection**: Automatic detection for 100+ languages
- **Unicode Normalization**: Proper handling of all scripts
- **Multilingual OCR**: Automatic language pack selection
- **Cross-Language Search**: Semantic search across languages
- **Language-Preserving Generation**: All AI features work in document language
- **RTL Support**: Full support for Arabic, Hebrew, Persian, Urdu
- **User Preferences**: Configurable output language
- **Mixed Language Support**: Documents with multiple languages

---

## Multilingual Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Multilingual Intelligence Layer                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input Processing                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   PDF       │  │   Image     │  │   Text      │  │   Web       │      │
│  │   Parser    │  │   OCR       │  │   Parser    │  │   Content   │      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                   Language Detection                                │       │
│  │  • Script Detection                                               │       │
│  │  • Writing Direction                                              │       │
│  │  • Mixed Language Detection                                        │       │
│  │  • Encoding Detection                                              │       │
│  └────────────────────────────────┬────────────────────────────────┘       │
│                                   ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                   Unicode Normalization                             │       │
│  │  • Arabic Normalization                                          │       │
│  │  • CJK Normalization                                              │       │
│  │  • Zero-Width Removal                                             │       │
│  │  • Whitespace Normalization                                       │       │
│  └────────────────────────────────┬────────────────────────────────┘       │
│                                   ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                   Multilingual Embeddings                         │       │
│  │  • Universal Sentence Embeddings                                 │       │
│  │  • Cross-Language Vector Search                                  │       │
│  │  • Semantic Matching                                             │       │
│  └────────────────────────────────┬────────────────────────────────┘       │
│                                   ↓                                          │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                   Language-Aware RAG                               │       │
│  │  • Query Language Detection                                       │       │
│  │  • Cross-Language Retrieval                                       │       │
│  │  • Semantic Ranking                                               │       │
│  │  • Generation in User Language                                    │       │
│  └────────────────────────────────┬────────────────────────────────┘       │
│                                   ↓                                          │
│  Output Processing                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Flashcard │  │   Summary   │  │   Chat      │  │   Report    │      │
│  │   Generator │  │   Generator │  │   Response  │  │   Generator │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                              ↓                                              │
│  Language Preservation (Document Language → Output Language)              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
backend/src/multilingual/
├── __init__.py                    # Module exports
├── models.py                      # Database models
├── detector.py                    # Language detection
├── normalizer.py                 # Unicode normalization
├── registry.py                   # Language registry (100+ languages)
├── search.py                     # Cross-language search
├── generation.py                 # Multilingual AI generation
├── preferences.py                # User language preferences
├── ocr_router.py                  # OCR language pack router
└── rtl_renderer.py               # RTL text rendering

backend/src/api/
└── multilingual.py              # REST API endpoints
```

---

## Database Schema

### languages

```sql
CREATE TABLE languages (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    iso_name VARCHAR(100) NOT NULL,
    native_name VARCHAR(100) NOT NULL,
    script_type VARCHAR(20) NOT NULL,
    writing_direction VARCHAR(10) DEFAULT 'ltr',
    has_ocr_support BOOLEAN DEFAULT FALSE,
    has_embeddings BOOLEAN DEFAULT FALSE,
    has_tts BOOLEAN DEFAULT FALSE,
    word_tokenizer VARCHAR(50),
    sentence_tokenizer VARCHAR(50),
    stemmer VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    is_rtl BOOLEAN DEFAULT FALSE,
    nlp_priority INTEGER DEFAULT 5,
    characters TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### language_preferences

```sql
CREATE TABLE language_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    preference_mode VARCHAR(50) DEFAULT 'auto',
    follow_upload_language BOOLEAN DEFAULT TRUE,
    follow_query_language BOOLEAN DEFAULT TRUE,
    preferred_output_language VARCHAR(10),
    ui_language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### document_languages

```sql
CREATE TABLE document_languages (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE UNIQUE,
    primary_language VARCHAR(10) NOT NULL,
    language_confidence FLOAT DEFAULT 0.0,
    script_type VARCHAR(20),
    writing_direction VARCHAR(10) DEFAULT 'ltr',
    is_mixed_language BOOLEAN DEFAULT FALSE,
    secondary_languages JSONB,
    detected_encoding VARCHAR(50),
    detection_method VARCHAR(50),
    confidence_breakdown JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### chunk_languages

```sql
CREATE TABLE chunk_languages (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    language VARCHAR(10) NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    is_primary BOOLEAN DEFAULT TRUE,
    normalized_text TEXT,
    original_text_length INTEGER DEFAULT 0,
    normalized_text_length INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_chunklang_chunk ON chunk_languages(chunk_id);
CREATE INDEX ix_chunklang_document ON chunk_languages(document_id);
```

### translation_cache

```sql
CREATE TABLE translation_cache (
    id SERIAL PRIMARY KEY,
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    source_text_hash VARCHAR(64) NOT NULL,
    source_text_length INTEGER DEFAULT 0,
    translated_text TEXT NOT NULL,
    translation_model VARCHAR(100),
    quality_score FLOAT,
    is_verified BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_language, target_language, source_text_hash)
);
```

### cross_language_mappings

```sql
CREATE TABLE cross_language_mappings (
    id SERIAL PRIMARY KEY,
    concept_id INTEGER,
    entity_id INTEGER,
    mappings JSONB NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### language_metrics

```sql
CREATE TABLE language_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL,
    language VARCHAR(10),
    accuracy FLOAT,
    latency_ms INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

### Language Detection

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/multilingual/detect` | Detect language from text |
| POST | `/multilingual/detect/batch` | Batch language detection |

### Languages

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/multilingual/languages` | List supported languages |
| GET | `/multilingual/languages/{code}` | Get language details |
| GET | `/multilingual/languages/search?q=` | Search languages |

### Preferences

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/multilingual/preferences` | Get user preferences |
| PUT | `/multilingual/preferences` | Update preferences |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/multilingual/search?q=` | Cross-language search |
| GET | `/multilingual/search/distribution` | Language distribution |

### Utility

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/multilingual/normalize` | Normalize Unicode |
| POST | `/multilingual/translate` | Translate content |
| GET | `/multilingual/rtl/check/{code}` | Check RTL |
| GET | `/multilingual/rtl/css/{code}` | Get RTL CSS |
| GET | `/multilingual/documents/{id}/language` | Document language |

---

## Language Detection

### Supported Scripts

| Script | Languages |
|--------|-----------|
| Latin | English, Spanish, French, German, Portuguese, Italian, etc. |
| Arabic | Arabic, Persian, Urdu, Pashto, Kurdish |
| Cyrillic | Russian, Ukrainian, Bulgarian, Serbian |
| Devanagari | Hindi, Marathi, Nepali, Sanskrit |
| CJK | Chinese, Japanese, Korean |
| Tamil | Tamil |
| Telugu | Telugu |
| Hebrew | Hebrew, Yiddish |
| Greek | Greek |
| Thai | Thai |

### Detection Features

- Language identification with confidence score
- Script detection
- Writing direction detection (RTL/LTR)
- Mixed language detection
- Secondary language identification
- Encoding detection

---

## Cross-Language Search

### Search Strategy

1. Detect query language
2. Determine search languages (query language + related)
3. Retrieve chunks in all languages
4. Score by semantic relevance
5. Rank and return top results

### Example

```
User Query (Arabic): "ما هو تعلم الآلة؟"
↓ (detected: Arabic)
Search: "machine learning", "تعلم الآلة", "机器学习", "機械学習", "머신러닝"
↓ (semantic match found)
Results: English, Chinese, Japanese, Korean documents about ML
```

---

## Language Preservation

### Generation Rules

| Document Language | Output Language |
|-------------------|-----------------|
| Japanese | Japanese |
| Arabic | Arabic |
| Hindi | Hindi |
| English | English |
| Mixed | Follows user preference |

### Supported AI Features

- Flashcard generation
- Summary generation
- Question generation
- Concept extraction
- Entity extraction
- Relationship mapping
- Research reports
- Chat responses

---

## RTL Support

### RTL Languages

- Arabic (ar)
- Persian/Farsi (fa)
- Urdu (ur)
- Hebrew (he)
- Pashto (ps)
- Yiddish (yi)
- Sindhi (sd)
- Central Kurdish (ckb)

### RTL Features

- Automatic direction detection
- HTML dir attribute
- CSS mirroring
- Markdown formatting
- PDF export metadata
- Bidirectional text normalization

---

## Performance Optimizations

### Caching

- Translation cache with hash lookup
- Language detection results
- Normalized text cache

### Batch Processing

- Batch language detection
- Batch normalization
- Batch translation

### Lazy Translation

- Only translate when necessary
- Cache frequently used translations
- Skip translation for same-language content

---

## Integration with Phases 1-6

### Knowledge Workspace (Phase 2)
- Store language with documents
- Search across all languages

### Knowledge Intelligence (Phase 3)
- Generate flashcards in document language
- Extract entities in document language
- Generate questions in document language

### Validation Layer (Phase 3.5)
- Validate language metadata
- Quality scores by language

### Interaction Layer (Phase 4)
- Notes in user's preferred language
- Collections with language awareness

### Research OS (Phase 5)
- Research reports in document language
- Evidence in source language
- Synthesis in user's language

### Multi-Agent (Phase 6)
- Agent responses in appropriate language
- Task outputs preserve source language

---

## Files Added

```
backend/src/multilingual/
├── __init__.py
├── models.py
├── detector.py
├── normalizer.py
├── registry.py
├── search.py
├── generation.py
├── preferences.py
├── ocr_router.py
└── rtl_renderer.py

backend/src/api/
└── multilingual.py

docs/architecture/
└── phase-7-multilingual-intelligence.md
```

---

## Git Commit Summary

```
Phase 7: Multilingual Intelligence Layer

## Database Models (6 tables)
- languages: Supported languages registry
- language_preferences: User language preferences
- document_languages: Document language detection
- chunk_languages: Chunk-level language info
- translation_cache: Translation cache
- language_metrics: Language processing metrics

## Services (8 services)
- LanguageDetector: Universal language detection
- UnicodeNormalizer: Unicode normalization
- LanguageRegistry: 30+ supported languages
- CrossLanguageSearchService: Cross-language search
- MultilingualGenerationService: Language-preserving generation
- LanguagePreferenceService: User preferences
- OCRLanguageRouter: OCR pack selection
- RTLRenderer: RTL text rendering

## API Endpoints (15+ endpoints)
- /multilingual/detect: Language detection
- /multilingual/languages: Language registry
- /multilingual/preferences: User preferences
- /multilingual/search: Cross-language search
- /multilingual/normalize: Unicode normalization
- /multilingual/translate: Translation
- /multilingual/rtl: RTL support

## Key Features
- Universal language detection (30+ languages)
- Unicode normalization (Arabic, CJK, Indic)
- Cross-language semantic search
- Language-preserving AI generation
- Full RTL support (Arabic, Hebrew, Persian, Urdu)
- User language preferences
- Translation caching
- Mixed language document support
- Script detection and routing
- OCR language pack selection

## Supported Languages
English, Arabic, Chinese, Japanese, Korean, Hindi, Spanish,
French, German, Portuguese, Russian, Italian, Turkish, Persian,
Urdu, Hebrew, Thai, Vietnamese, Indonesian, Tamil, Telugu,
Bengali, Ukrainian, Dutch, Polish, Greek, Czech, Swedish,
Hungarian, Romanian, and more...
```
