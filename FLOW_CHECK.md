# Flow Verification & JSON Structure

## Complete Pipeline Flow

### 1. POST /process
**Input:**
```json
{
  "file": <multipart/form-data file>,
  "entity_id": "entity_123" (optional)
}
```

**Flow:**
1. **Step 1: Upload** (`step1_upload.py`)
   - Input: `file_bytes`, `filename`
   - Output: `{file_id, raw_file, meta}` ✓

2. **Step 2: Preprocess** (`step2_preprocessing.py`)
   - Input: `file_id`, `file_bytes`, `filename`, `stored_path`
   - Uses: `extractors/pdf_extract.py`, `extractors/excel_extract.py`, etc.
   - Output: `{file_id, text, language, metadata, structured_data}` ✓

3. **Step 3: Classify** (`step3_sector_classifier.py`)
   - Input: `text`, `metadata`
   - Uses: Groq API (`llama-3.3-70b-versatile`)
   - Output: `{sector, confidence}` ✓

4. **Step 4: Extract** (`modules/{sector}/extractor.py`)
   - Input: `text`, `metadata`
   - Output: `{events: [...]}` ✓

5. **Step 4: Detect Risks** (`modules/{sector}/rules.py`)
   - Input: `events`, `timeline`
   - Output: `[{risk, severity, event_ids, explanation}]` ✓

6. **Step 5: Core Reasoner** (`step5_core_reasoner.py`)
   - `store_events()`: Stores in SQLite, updates timeline
   - `create_embeddings()`: Stores in ChromaDB (if available)
   - Output: `{timeline_updated, events_stored, vector_db_updated, chunks_stored}` ✓

7. **Step 6: Alerts Engine** (`step6_alerts_engine.py`)
   - Input: `risks`, `events`, `timeline`, `sector`, `file_id`
   - Output: `[{alert_id, title, severity, reason, source_file, evidence, recommended_actions, created_at}]` ✓

**Final Response:**
```json
{
  "status": "success",
  "file_id": "file_abc123",
  "entity_id": "entity_xyz789",
  "sector": "finance",
  "confidence": 0.93,
  "events": [
    {
      "event_id": "ev_123",
      "type": "invoice",
      "invoice_no": "INV21",
      ...
      "confidence": 0.9,
      "provenance": [...]
    }
  ],
  "risks": [
    {
      "risk": "GST mismatch",
      "severity": "high",
      "event_ids": ["ev_123"],
      "explanation": "..."
    }
  ],
  "alerts": [
    {
      "alert_id": "alert_abc",
      "title": "GST mismatch detected",
      "severity": "high",
      "reason": "...",
      "source_file": "file_abc123",
      "evidence": [...],
      "recommended_actions": [...],
      "created_at": "2025-12-07T10:00:00"
    }
  ],
  "core_reasoner": {
    "timeline_updated": true,
    "events_stored": ["ev_123"],
    "vector_db_updated": true,
    "chunks_stored": 5
  }
}
```

### 2. GET /timeline/{entity_id}
**Input:** `entity_id` (path param), `limit` (query param, default 100)

**Flow:**
- Queries SQLite database via `core_reasoner.get_timeline()`
- Returns: `{status, entity_id, timeline: [...]}` ✓

### 3. POST /chat/{entity_id}
**Input:**
```json
{
  "query": "What are the risks in my documents?"
}
```

**Flow:**
1. `chatbot.answer_query()` called
2. Searches vector DB via `core_reasoner.search_vector_db()`
3. Gets timeline via `core_reasoner.get_timeline()`
4. Builds prompt with context
5. Calls Groq API
6. Returns: `{status, entity_id, query, answer, sources: [...]}` ✓

## Connection Verification

### ✅ All Imports Verified:
- `step1_upload.py` → standalone ✓
- `step2_preprocessing.py` → imports from `extractors/` ✓
- `step3_sector_classifier.py` → uses Groq API ✓
- `step5_core_reasoner.py` → standalone, optional ChromaDB ✓
- `step6_alerts_engine.py` → imports all sector rules ✓
- `step8_chatbot.py` → imports `step5_core_reasoner` ✓
- `main.py` → imports all steps and modules ✓

### ✅ Sector Modules:
- All 6 sectors have `extractor.py` and `rules.py` ✓
- All inherit from `BaseExtractor` and `BaseRules` ✓
- All properly imported in `main.py` ✓

### ✅ API Endpoints:
- `/upload` - File upload only ✓
- `/process` - Full pipeline ✓
- `/timeline/{entity_id}` - Get timeline ✓
- `/alerts/{entity_id}` - Get alerts (placeholder) ✓
- `/chat/{entity_id}` - Chatbot ✓

### ✅ JSON Flow:
- All functions return proper dict structures ✓
- All API endpoints return consistent JSON ✓
- Error handling with HTTPException ✓

## Potential Issues Fixed:
1. ✅ `entity_id` in `/process` now uses `Form()` for proper form data handling
2. ✅ All imports verified and correct
3. ✅ All JSON structures consistent
4. ✅ Error handling in place

## Ready to Test! 🚀

