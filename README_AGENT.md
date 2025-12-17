# Agentic AI Document Intelligence System
## Production-Grade, Prize-Level Agent for Agentathon 2025

---

## 🎯 What This Is

This is **NOT a chatbot**. This is **NOT a simple RAG app**.

This is a **fully autonomous, multi-step, tool-using agent** with:
- ✅ Visible decision-making
- ✅ Memory and state management
- ✅ Automatic recovery loops
- ✅ Full observability

---

## 🏗️ Architecture

### Agent States (LangGraph)

```
PLANNER → EXECUTOR → VALIDATOR → RECOVERY → (Retry or End)
```

1. **Planner**: Analyzes task, creates execution plan
2. **Executor**: Executes plan step-by-step using tools
3. **Validator**: Validates results, decides if recovery needed
4. **Recovery**: Handles failures, retries with backoff

### Tools (Real Python Functions)

The agent dynamically chooses from 10+ tools:
- `preprocess_document` - Extract text from documents
- `classify_sector` - Classify document sector
- `extract_events` - Extract structured events
- `detect_risks` - Detect risks and issues
- `store_events` - Store in database
- `create_embeddings` - Create vector embeddings
- `generate_alerts` - Generate alerts
- `store_alerts` - Store alerts
- `get_timeline` - Get entity timeline
- `generate_insights` - Generate LLM insights

### Memory

- **Short-term**: LangGraph state (in-memory during execution)
- **Long-term**: SQLite + FAISS vector store (persistent)

---

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add:
GROQ_API_KEY=your_groq_key
# OR
GOOGLE_API_KEY=your_gemini_key
LLM_PROVIDER=groq  # or "gemini"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run with Docker (Recommended)

```bash
# Build and run
docker-compose up --build

# Or with Docker
docker build -t agentathon-agent .
docker run -p 8000:8000 --env-file .env agentathon-agent
```

### 4. Run Locally

```bash
# Start server
uvicorn main:app --reload

# Server runs on http://localhost:8000
```

---

## 📡 API Usage

### Process Document (Agent Mode)

```bash
curl -X POST "http://localhost:8000/process?use_agent=true" \
  -F "files=@document.pdf" \
  -F "entity_id=entity_123"
```

**Response includes full observability:**
```json
{
  "status": "success",
  "agent_mode": true,
  "results": [{
    "file_id": "file_abc123",
    "sector": "healthcare",
    "events": [...],
    "alerts": [...],
    "observability": {
      "execution_log": [
        {"step": "planner", "timestamp": "...", "result": {...}},
        {"step": "executor", "tool": "preprocess_document", ...},
        {"step": "validator", "validation_passed": true, ...}
      ],
      "tools_used": [
        {"tool": "preprocess_document", "success": true, ...},
        {"tool": "extract_events", "success": true, ...}
      ],
      "retry_count": 0,
      "validation_passed": true,
      "recovery_actions": []
    }
  }]
}
```

### Get Observability

```bash
curl "http://localhost:8000/observability/file_abc123"
```

---

## 🔍 Observability

Every agent execution provides:

1. **Execution Log**: Step-by-step trace
   - Planner decisions
   - Tool calls
   - Validation results
   - Recovery actions

2. **Tool Usage**: All tool calls with:
   - Tool name
   - Success/failure
   - Timestamps
   - Results

3. **Retry Tracking**: 
   - Retry count
   - Recovery actions taken
   - Final outcome

4. **Validation Status**:
   - Validation passed/failed
   - Errors detected
   - Recovery triggers

---

## 🎯 How Autonomy is Achieved

### 1. Planning
Agent creates execution plan based on document type and requirements.

### 2. Execution
Agent executes plan step-by-step, calling tools dynamically.

### 3. Validation
Agent validates each step, checking for errors or missing data.

### 4. Recovery
If validation fails:
- Agent identifies failed steps
- Retries with backoff
- Adjusts strategy if needed
- Fails gracefully after max retries

### 5. No Human Intervention
Once started, agent runs autonomously:
- Makes decisions
- Chooses tools
- Handles errors
- Recovers from failures
- Completes or fails gracefully

---

## 🏆 For Judges

### 3-Minute Demo Script

1. **Show Agent Architecture** (30s)
   - "This is a LangGraph agent with 4 states: Planner, Executor, Validator, Recovery"

2. **Process a Document** (60s)
   - Upload a document via API
   - Show agent making decisions
   - Show tool calls in real-time
   - Show validation and recovery

3. **Show Observability** (60s)
   - Show execution log
   - Show tool usage
   - Show retry logic
   - Show final result

4. **Explain Autonomy** (30s)
   - "Agent plans, executes, validates, and recovers autonomously"
   - "No human intervention needed once started"

### Key Points to Highlight

✅ **True Agent**: Not a chatbot, not simple RAG  
✅ **LangGraph**: Industry-standard orchestration  
✅ **Tool-Based**: Real Python functions, not just prompts  
✅ **Observable**: Every decision is logged  
✅ **Autonomous**: Runs without human intervention  
✅ **Production-Ready**: Docker, logging, error handling  

---

## 📁 Project Structure

```
agentathon/
├── agent/              # Agent system
│   ├── state.py        # Agent state definition
│   ├── graph.py        # LangGraph workflow
│   ├── nodes.py        # Agent nodes (Planner, Executor, etc.)
│   ├── tools.py        # Tool registry
│   └── orchestrator.py # Main orchestrator
├── modules/            # Sector modules
│   ├── healthcare/
│   ├── finance/
│   └── ...
├── main.py             # FastAPI app
├── step*.py            # Pipeline steps
├── Dockerfile          # Production deployment
├── docker-compose.yml  # Local development
└── requirements.txt    # Dependencies
```

---

## 🔧 Configuration

### LLM Provider

Set `LLM_PROVIDER` in `.env`:
- `groq` - Uses Groq (Llama 3.3 70B)
- `gemini` - Uses Google Gemini 1.5 Pro

### Retry Configuration

In `agent/nodes.py`:
```python
max_retries = 3  # Adjust as needed
```

---

## 🚢 Deployment

### GCP Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/agentathon-agent

# Deploy
gcloud run deploy agentathon-agent \
  --image gcr.io/PROJECT_ID/agentathon-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars GROQ_API_KEY=your_key
```

### GCP VM

```bash
# Build Docker image
docker build -t agentathon-agent .

# Run on VM
docker run -d -p 8000:8000 --env-file .env agentathon-agent
```

---

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/
```

### Observability Endpoint

```bash
curl http://localhost:8000/observability/{file_id}
```

### Structured Logs

All logs are in JSON format for easy parsing:
```json
{
  "timestamp": "2025-01-17T10:00:00",
  "level": "info",
  "event": "agent_step",
  "step": "executor",
  "tool": "extract_events",
  "success": true
}
```

---

## ✅ Non-Negotiable Requirements Met

- ✅ **LangGraph Required**: Full LangGraph implementation
- ✅ **Explicit States**: Planner, Executor, Validator, Recovery
- ✅ **Real Tools**: Python functions, not prompts
- ✅ **Observability**: Step-by-step logs, tool usage, retries
- ✅ **Autonomy**: Plan → Execute → Validate → Retry
- ✅ **Deployment Ready**: Dockerfile, .env support
- ✅ **No Silent Failures**: All errors logged and handled
- ✅ **Explainable**: Every decision is observable

---

## 🎓 Learning Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Agent Patterns](https://langchain-ai.github.io/langgraph/tutorials/)
- [Structured Logging](https://www.structlog.org/)

---

## 📝 License

MIT License - Built for Agentathon 2025

---


