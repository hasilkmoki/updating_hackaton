"""
Agent Orchestrator
Main entry point for agent execution
"""
from datetime import datetime
import uuid
from typing import Dict, Any

from agent.state import AgentState
from agent.graph import get_agent_graph
from step1_upload import upload_file
from config.logging import logger


class AgentOrchestrator:
    """Orchestrates agent execution with full observability"""
    
    def __init__(self):
        self.graph = None
    
    def _get_graph(self):
        """Get agent graph (lazy initialization)"""
        if self.graph is None:
            self.graph = get_agent_graph()
        return self.graph
    
    async def process_document(
        self,
        file_bytes: bytes,
        filename: str,
        entity_id: str = None
    ) -> Dict[str, Any]:
        """
        Process document through agent pipeline
        Returns full execution trace with observability
        """
        if not entity_id:
            entity_id = f"entity_{uuid.uuid4().hex[:8]}"
        
        # Generate file_id
        file_id = f"file_{uuid.uuid4().hex[:8]}"
        
        # Upload file first
        upload_result = upload_file(file_bytes, filename)
        file_id = upload_result["file_id"]
        stored_path = upload_result["raw_file"]
        
        # Initialize agent state
        initial_state: AgentState = {
            "file_bytes": file_bytes,
            "filename": filename,
            "entity_id": entity_id,
            "file_id": file_id,
            "stored_path": stored_path,
            "text": "",
            "metadata": {},
            "sector": "",
            "confidence": 0.0,
            "plan": [],
            "current_step": 0,
            "steps_completed": [],
            "events": [],
            "risks": [],
            "alerts": [],
            "insights": {},
            "tools_used": [],
            "tool_results": {},
            "validation_passed": False,
            "validation_errors": [],
            "retry_count": 0,
            "max_retries": 3,
            "recovery_actions": [],
            "execution_log": [],
            "start_time": datetime.now(),
            "end_time": None,
            "status": "processing",
            "error": None,
            "final_result": None,
            "timeline": []
        }
        
        logger.info("agent_started", 
                   file_id=file_id, 
                   entity_id=entity_id, 
                   filename=filename)
        
        try:
            # Execute agent graph
            graph = self._get_graph()
            final_state = await graph.ainvoke(initial_state)
            
            # Calculate execution time safely
            # Always use initial_state start_time as it's guaranteed to be set
            start_time = initial_state.get("start_time")
            end_time = final_state.get("end_time")
            
            # If end_time not set, use current time
            if end_time is None:
                end_time = datetime.now()
                final_state["end_time"] = end_time
            
            # Calculate execution time
            if start_time and end_time:
                try:
                    execution_time = (end_time - start_time).total_seconds()
                except (TypeError, AttributeError) as e:
                    logger.warning("execution_time_calc_error", error=str(e))
                    execution_time = 0.0
            else:
                execution_time = 0.0
            
            # Build final result
            result = {
                "status": final_state.get("status", "unknown"),
                "entity_id": entity_id,
                "file_id": file_id,
                "filename": filename,
                "sector": final_state.get("sector", ""),
                "confidence": final_state.get("confidence", 0.0),
                "events": final_state.get("events", []),
                "risks": final_state.get("risks", []),
                "alerts": final_state.get("alerts", []),
                "insights": final_state.get("insights", {}),
                "execution_time": execution_time,
                "observability": {
                    "execution_log": final_state.get("execution_log", []),
                    "tools_used": final_state.get("tools_used", []),
                    "retry_count": final_state.get("retry_count", 0),
                    "validation_passed": final_state.get("validation_passed", False),
                    "validation_errors": final_state.get("validation_errors", []),
                    "recovery_actions": final_state.get("recovery_actions", [])
                }
            }
            
            final_state["final_result"] = result
            
            logger.info("agent_completed",
                       file_id=file_id,
                       status=result["status"],
                       execution_time=result["execution_time"])
            
            return result
            
        except Exception as e:
            logger.error("agent_error", file_id=file_id, error=str(e))
            
            # Calculate execution time even on error
            start_time = initial_state.get("start_time")
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() if start_time else 0.0
            
            return {
                "status": "failed",
                "entity_id": entity_id,
                "file_id": file_id,
                "filename": filename,
                "error": str(e),
                "execution_time": execution_time,
                "observability": {
                    "execution_log": initial_state.get("execution_log", []),
                    "tools_used": initial_state.get("tools_used", []),
                    "error": str(e)
                }
            }


# Global orchestrator instance
orchestrator = AgentOrchestrator()

