"""
Agent Tools
Real Python functions that the agent can call dynamically
"""
from typing import Dict, List, Any

from config.logging import logger

# Import existing extractors and rules
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

from step2_preprocessing import preprocess_file
from step3_sector_classifier import classify_sector
from step5_core_reasoner import CoreReasoner
from step6_alerts_engine import AlertsEngine
from step7_insights_engine import InsightsEngine

# Initialize components
core_reasoner = CoreReasoner()
alerts_engine = AlertsEngine()

# Sector extractors
EXTRACTORS = {
    "healthcare": HealthcareExtractor(),
    "finance": FinanceExtractor(),
    "agriculture": AgricultureExtractor(),
    "logistics": LogisticsExtractor(),
    "government": GovernmentExtractor(),
    "kirana": KiranaExtractor()
}

# Sector rules
RULES = {
    "healthcare": HealthcareRules(),
    "finance": FinanceRules(),
    "agriculture": AgricultureRules(),
    "logistics": LogisticsRules(),
    "government": GovernmentRules(),
    "kirana": KiranaRules()
}


def tool_preprocess_document(file_id: str, file_bytes: bytes, filename: str, stored_path: str) -> Dict[str, Any]:
    """Tool: Preprocess document to extract text"""
    logger.info("tool_called", tool="preprocess_document", file_id=file_id)
    try:
        result = preprocess_file(file_id, file_bytes, filename, stored_path)
        logger.info("tool_success", tool="preprocess_document", text_length=len(result.get("text", "")))
        return {"success": True, "result": result}
    except Exception as e:
        logger.error("tool_error", tool="preprocess_document", error=str(e))
        return {"success": False, "error": str(e)}


def tool_classify_sector(text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Classify document sector"""
    logger.info("tool_called", tool="classify_sector", text_length=len(text))
    try:
        result = classify_sector(text, metadata)
        logger.info("tool_success", tool="classify_sector", sector=result.get("sector"))
        return {"success": True, "result": result}
    except Exception as e:
        logger.error("tool_error", tool="classify_sector", error=str(e))
        return {"success": False, "error": str(e)}


def tool_extract_events(sector: str, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Tool: Extract events from document using sector-specific extractor"""
    logger.info("tool_called", tool="extract_events", sector=sector)
    try:
        extractor = EXTRACTORS.get(sector)
        if not extractor:
            return {"success": False, "error": f"Unknown sector: {sector}"}
        
        result = extractor.extract(text, metadata)
        events = result.get("events", [])
        logger.info("tool_success", tool="extract_events", events_count=len(events))
        return {"success": True, "result": result, "events": events}
    except Exception as e:
        logger.error("tool_error", tool="extract_events", error=str(e))
        return {"success": False, "error": str(e)}


def tool_detect_risks(sector: str, events: List[Dict], timeline: List[Dict]) -> Dict[str, Any]:
    """Tool: Detect risks using sector-specific rules"""
    logger.info("tool_called", tool="detect_risks", sector=sector, events_count=len(events))
    try:
        rules = RULES.get(sector)
        if not rules:
            return {"success": False, "error": f"No rules for sector: {sector}"}
        
        risks = rules.detect_risks(events, timeline)
        logger.info("tool_success", tool="detect_risks", risks_count=len(risks))
        return {"success": True, "risks": risks}
    except Exception as e:
        logger.error("tool_error", tool="detect_risks", error=str(e))
        return {"success": False, "error": str(e)}


def tool_store_events(events: List[Dict], entity_id: str, file_id: str, sector: str) -> Dict[str, Any]:
    """Tool: Store events in database"""
    logger.info("tool_called", tool="store_events", events_count=len(events))
    try:
        result = core_reasoner.store_events(events, entity_id, file_id, sector)
        logger.info("tool_success", tool="store_events", stored_count=len(result.get("events_stored", [])))
        return {"success": True, "result": result}
    except Exception as e:
        logger.error("tool_error", tool="store_events", error=str(e))
        return {"success": False, "error": str(e)}


def tool_create_embeddings(events: List[Dict], file_id: str, entity_id: str, text: str) -> Dict[str, Any]:
    """Tool: Create embeddings for vector search"""
    logger.info("tool_called", tool="create_embeddings")
    try:
        result = core_reasoner.create_embeddings(events, file_id, entity_id, text)
        logger.info("tool_success", tool="create_embeddings", chunks=result.get("chunks_stored", 0))
        return {"success": True, "result": result}
    except Exception as e:
        logger.error("tool_error", tool="create_embeddings", error=str(e))
        return {"success": False, "error": str(e)}


def tool_generate_alerts(risks: List[Dict], events: List[Dict], timeline: List[Dict], sector: str, file_id: str) -> Dict[str, Any]:
    """Tool: Generate alerts from risks"""
    logger.info("tool_called", tool="generate_alerts", risks_count=len(risks))
    try:
        alerts = alerts_engine.generate_alerts(risks, events, timeline, sector, file_id)
        logger.info("tool_success", tool="generate_alerts", alerts_count=len(alerts))
        return {"success": True, "alerts": alerts}
    except Exception as e:
        logger.error("tool_error", tool="generate_alerts", error=str(e))
        return {"success": False, "error": str(e)}


def tool_store_alerts(alerts: List[Dict], entity_id: str) -> Dict[str, Any]:
    """Tool: Store alerts in database"""
    logger.info("tool_called", tool="store_alerts", alerts_count=len(alerts))
    try:
        result = core_reasoner.store_alerts(alerts, entity_id)
        logger.info("tool_success", tool="store_alerts", stored_count=len(result.get("alerts_stored", [])))
        return {"success": True, "result": result}
    except Exception as e:
        logger.error("tool_error", tool="store_alerts", error=str(e))
        return {"success": False, "error": str(e)}


def tool_get_timeline(entity_id: str, limit: int = 50) -> Dict[str, Any]:
    """Tool: Get timeline for entity"""
    logger.info("tool_called", tool="get_timeline", entity_id=entity_id)
    try:
        timeline = core_reasoner.get_timeline(entity_id, limit)
        logger.info("tool_success", tool="get_timeline", events_count=len(timeline))
        return {"success": True, "timeline": timeline}
    except Exception as e:
        logger.error("tool_error", tool="get_timeline", error=str(e))
        return {"success": False, "error": str(e)}


def tool_generate_insights(events: List[Dict], risks: List[Dict], alerts: List[Dict], sector: str, text: str) -> Dict[str, Any]:
    """Tool: Generate insights using LLM"""
    logger.info("tool_called", tool="generate_insights", sector=sector)
    try:
        insights_engine = InsightsEngine()
        insights = insights_engine.generate_insights(events, risks, alerts, sector, text)
        logger.info("tool_success", tool="generate_insights")
        return {"success": True, "insights": insights}
    except Exception as e:
        logger.error("tool_error", tool="generate_insights", error=str(e))
        return {"success": False, "error": str(e)}


# Tool registry for agent
TOOLS = {
    "preprocess_document": tool_preprocess_document,
    "classify_sector": tool_classify_sector,
    "extract_events": tool_extract_events,
    "detect_risks": tool_detect_risks,
    "store_events": tool_store_events,
    "create_embeddings": tool_create_embeddings,
    "generate_alerts": tool_generate_alerts,
    "store_alerts": tool_store_alerts,
    "get_timeline": tool_get_timeline,
    "generate_insights": tool_generate_insights,
}

