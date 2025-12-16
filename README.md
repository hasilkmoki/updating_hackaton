# Document Intelligence Pipeline

Complete 8-step pipeline for document processing, sector classification, extraction, and intelligent alerts.

## Architecture

1. **Upload/Ingestion** - File storage and metadata
2. **Preprocessing** - OCR/parsing using existing extractors
3. **Sector Classification** - Groq LLM-based routing
4. **Sector Modules** - Domain-specific extraction (healthcare, finance, agriculture, logistics, government, kirana)
5. **Core Reasoner** - Timeline, vector DB, knowledge graph
6. **Alerts Engine** - Risk detection and alerting
7. **Dashboard** - API endpoints for insights
8. **Chatbot** - RAG-based Q&A

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# Create .env file
GROQ_API_KEY="your_groq_api_key"
```

3. Run the server:
```bash
uvicorn main:app --reload
```

## API Endpoints

- `POST /upload` - Upload a document
- `POST /process` - Full pipeline processing
- `GET /timeline/{entity_id}` - Get entity timeline
- `GET /alerts/{entity_id}` - Get alerts for entity
- `POST /chat/{entity_id}` - Chatbot query

## Sector Modules

Each sector has:
- `extractor.py` - Extracts structured events
- `rules.py` - Detects risks

### Supported Sectors

- **Healthcare** - Lab results, medications, diagnoses
- **Finance** - Invoices, GST, payments
- **Agriculture** - Soil moisture, NDVI, temperature
- **Logistics** - Shipments, GPS, temperature
- **Government** - Applications, deadlines
- **Kirana** - Bills, inventory

## Project Structure

```
agentathon/
├── extractors/          # Existing extractors (PDF, Excel, DOC, Image)
├── modules/            # Sector-specific modules
│   ├── healthcare/
│   ├── finance/
│   ├── agriculture/
│   ├── logistics/
│   ├── government/
│   └── kirana/
├── step1_upload.py     # Upload/Ingestion
├── step2_preprocessing.py  # Preprocessing
├── step3_sector_classifier.py  # Sector classification
├── step5_core_reasoner.py  # Core reasoner
├── step6_alerts_engine.py  # Alerts engine
├── step8_chatbot.py   # Chatbot
└── main.py            # Main FastAPI app
```

## Usage Example

```python
import requests

# Process a document
with open("invoice.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/process",
        files={"file": f},
        data={"entity_id": "entity_123"}
    )
    result = response.json()
    print(f"Sector: {result['sector']}")
    print(f"Events: {result['events']}")
    print(f"Alerts: {result['alerts']}")

# Chat with documents
response = requests.post(
    "http://localhost:8000/chat/entity_123",
    json={"query": "What are the risks in my documents?"}
)
print(response.json()["answer"])
```

