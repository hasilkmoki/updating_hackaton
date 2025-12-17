"""
Main FastAPI Application
Production-Grade Agentic AI System with LangGraph
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uuid

# Initialize structured logging
from config.logging import configure_logging
configure_logging()

# Import pipeline steps
from step1_upload import upload_file
from step2_preprocessing import preprocess_file
from step3_sector_classifier import classify_sector
from step5_core_reasoner import CoreReasoner
from step6_alerts_engine import AlertsEngine
from step7_insights_engine import InsightsEngine
from step8_chatbot import Chatbot

# Import sector modules
from modules.healthcare.extractor import HealthcareExtractor
from modules.finance.extractor import FinanceExtractor
from modules.agriculture.extractor import AgricultureExtractor
from modules.logistics.extractor import LogisticsExtractor
from modules.government.extractor import GovernmentExtractor
from modules.kirana.extractor import KiranaExtractor

from modules.healthcare.rules import HealthcareRules
from modules.finance.rules import FinanceRules
from modules.agriculture.rules import AgricultureRules
from modules.logistics.rules import LogisticsRules
from modules.government.rules import GovernmentRules
from modules.kirana.rules import KiranaRules

app = FastAPI(title="Document Intelligence Pipeline", version="1.0.0")


class ChatQuery(BaseModel):
    query: str

# Initialize core components
core_reasoner = CoreReasoner()
alerts_engine = AlertsEngine()
insights_engine = InsightsEngine()
chatbot = Chatbot(core_reasoner)

# Sector extractors map
EXTRACTORS = {
    "healthcare": HealthcareExtractor(),
    "finance": FinanceExtractor(),
    "agriculture": AgricultureExtractor(),
    "logistics": LogisticsExtractor(),
    "government": GovernmentExtractor(),
    "kirana": KiranaExtractor()
}

# Sector rules map
RULES = {
    "healthcare": HealthcareRules(),
    "finance": FinanceRules(),
    "agriculture": AgricultureRules(),
    "logistics": LogisticsRules(),
    "government": GovernmentRules(),
    "kirana": KiranaRules()
}


@app.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...), entity_id: Optional[str] = None):
    """
    STEP 1: Upload one or more documents
    """
    try:
        if not entity_id:
            entity_id = f"entity_{uuid.uuid4().hex[:8]}"

        uploads = []
        for file in files:
            file_bytes = await file.read()
            upload_result = upload_file(file_bytes, file.filename)
            uploads.append(upload_result)

        return {
            "status": "success",
            "entity_id": entity_id,
            "uploads": uploads,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process")
async def process_documents(
    files: List[UploadFile] = File(...),
    entity_id: Optional[str] = Form(None),
    use_agent: bool = Form(True)  # Toggle between agent and legacy pipeline
):
    """
    AGENTIC PROCESSING: Full autonomous agent pipeline with LangGraph
    - Planner → Executor → Validator → Recovery loop
    - Full observability and tool usage tracking
    - Automatic retry and error recovery
    """
    try:
        if not entity_id:
            entity_id = f"entity_{uuid.uuid4().hex[:8]}"

        # Use agent if enabled
        if use_agent:
            from agent.orchestrator import orchestrator
            
            results = []
            for file in files:
                file_bytes = await file.read()
                result = await orchestrator.process_document(
                    file_bytes, 
                    file.filename, 
                    entity_id
                )
                results.append(result)
            
            return {
                "status": "success",
                "entity_id": entity_id,
                "agent_mode": True,
                "results": results
            }
        
        # Legacy pipeline (for backward compatibility)
        results = []

        for file in files:
            try:
                # STEP 1: Upload
                file_bytes = await file.read()
                upload_result = upload_file(file_bytes, file.filename)
                file_id = upload_result["file_id"]
                stored_path = upload_result["raw_file"]

                # STEP 2: Preprocess
                preprocess_result = preprocess_file(
                    file_id, file_bytes, file.filename, stored_path
                )
                text = preprocess_result["text"]
                metadata = preprocess_result["metadata"]

                # STEP 3: Classify Sector
                classification = classify_sector(text, metadata)
                sector = classification["sector"]
                confidence = classification["confidence"]

                # STEP 4: Sector Module - Extract
                extractor = EXTRACTORS.get(sector)
                if not extractor:
                    raise HTTPException(status_code=400, detail=f"Unknown sector: {sector}")

                extract_result = extractor.extract(text, {"file_id": file_id, **metadata})
                events = extract_result.get("events", [])

                # STEP 4: Sector Module - Detect Risks
                rules = RULES.get(sector)
                timeline = core_reasoner.get_timeline(entity_id, limit=50)
                risks = rules.detect_risks(events, timeline) if rules else []

                # STEP 5: Core Reasoner
                store_result = core_reasoner.store_events(events, entity_id, file_id, sector)
                embed_result = core_reasoner.create_embeddings(events, file_id, entity_id, text)

                # STEP 6: Alerts Engine
                alerts = alerts_engine.generate_alerts(risks, events, timeline, sector, file_id)

                # STEP 7: Store alerts in database
                alerts_stored = core_reasoner.store_alerts(alerts, entity_id)

                # STEP 8: Insights Engine (LLM-powered analysis)
                insights = insights_engine.generate_insights(events, risks, alerts, sector, text)

                # Get updated timeline for preview (last 10 events)
                timeline_preview = core_reasoner.get_timeline(entity_id, limit=10)

                results.append({
                    "status": "success",
                    "file_id": file_id,
                    "filename": file.filename,
                    "sector": sector,
                    "confidence": confidence,
                    "insights": insights,
                    "events": events,
                    "risks": risks,
                    "alerts": alerts,
                    "timeline_preview": timeline_preview,
                    "core_reasoner": {
                        **store_result,
                        **embed_result,
                        **alerts_stored
                    }
                })
            except Exception as e:
                results.append({
                    "status": "error",
                    "filename": file.filename,
                    "message": str(e)
                })

        return {
            "status": "success",
            "entity_id": entity_id,
            "agent_mode": False,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/timeline/{entity_id}")
async def get_timeline(entity_id: str, limit: int = 100):
    """Get timeline for entity"""
    timeline = core_reasoner.get_timeline(entity_id, limit)
    return {
        "status": "success",
        "entity_id": entity_id,
        "timeline": timeline
    }
@app.get("/alerts/{entity_id}")
async def get_alerts(entity_id: str, status: str = "active", limit: int = 100):
    """Get alerts for entity from database"""
    alerts = core_reasoner.get_alerts(entity_id, status, limit)
    return {
        "status": "success",
        "entity_id": entity_id,
        "count": len(alerts),
        "alerts": alerts
    }


@app.post("/chat/{entity_id}")
async def chat(entity_id: str, chat_query: ChatQuery):
    """Chatbot endpoint"""
    result = chatbot.answer_query(entity_id, chat_query.query)
    return {
        "status": "success",
        "entity_id": entity_id,
        "query": chat_query.query,
        **result
    }


@app.get("/observability/{file_id}")
async def get_observability(file_id: str):
    """
    OBSERVABILITY ENDPOINT
    Get full agent execution trace for a file
    Shows: steps, tools used, retries, validation, recovery actions
    """
    # In production, this would query from a log store
    # For now, return structure
    return {
        "file_id": file_id,
        "message": "Observability data - check execution_log in /process response",
        "note": "Full observability is included in /process response under 'observability' key"
    }


@app.get("/")
async def root():
    return {
        "message": "Document Intelligence Pipeline API - Agentic AI System",
        "version": "2.0.0",
        "architecture": "LangGraph Agent (Planner → Executor → Validator → Recovery)",
        "endpoints": {
            "upload": "/upload",
            "process": "/process (use_agent=true for agent mode)",
            "timeline": "/timeline/{entity_id}",
            "alerts": "/alerts/{entity_id}",
            "chat": "/chat/{entity_id}",
            "observability": "/observability/{file_id}"
        },
        "agent_features": [
            "Autonomous planning and execution",
            "Tool-based processing",
            "Automatic validation",
            "Retry and recovery",
            "Full observability"
        ]
    }

