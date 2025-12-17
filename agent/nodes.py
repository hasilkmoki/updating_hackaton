"""
Agent Nodes
Each node represents a distinct agent state/behavior
"""
from typing import Literal
from datetime import datetime
import json

from agent.state import AgentState
from agent.tools import TOOLS
from config.logging import logger


def log_step(state: AgentState, step_name: str, result: dict):
    """Helper to log agent steps"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "step": step_name,
        "result": result,
        "retry_count": state.get("retry_count", 0)
    }
    state["execution_log"].append(log_entry)
    logger.info("agent_step", **log_entry)


def planner_node(state: AgentState) -> AgentState:
    """
    PLANNER NODE
    Agent analyzes the task and creates an execution plan
    """
    logger.info("planner_started", file_id=state.get("file_id"))
    
    try:
        # Create execution plan based on document type
        plan = [
            {"step": "preprocess", "tool": "preprocess_document", "description": "Extract text from document"},
            {"step": "classify", "tool": "classify_sector", "description": "Classify document sector"},
            {"step": "extract", "tool": "extract_events", "description": "Extract structured events"},
            {"step": "detect_risks", "tool": "detect_risks", "description": "Detect risks and issues"},
            {"step": "store", "tool": "store_events", "description": "Store events in database"},
            {"step": "embeddings", "tool": "create_embeddings", "description": "Create vector embeddings"},
            {"step": "alerts", "tool": "generate_alerts", "description": "Generate alerts"},
            {"step": "store_alerts", "tool": "store_alerts", "description": "Store alerts"},
            {"step": "insights", "tool": "generate_insights", "description": "Generate insights"}
        ]
        
        state["plan"] = plan
        state["current_step"] = 0
        state["steps_completed"] = []
        
        log_step(state, "planner", {"plan_created": True, "steps": len(plan)})
        logger.info("planner_completed", plan_steps=len(plan))
        
    except Exception as e:
        logger.error("planner_error", error=str(e))
        state["error"] = f"Planner failed: {str(e)}"
        state["status"] = "failed"
    
    return state


def executor_node(state: AgentState) -> AgentState:
    """
    EXECUTOR NODE
    Agent executes the plan step by step, calling tools dynamically
    Executes all remaining steps in the plan
    """
    logger.info("executor_started", current_step=state.get("current_step", 0))
    
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    
    if current_step >= len(plan):
        state["status"] = "success"
        logger.info("executor_completed", total_steps=len(plan))
        return state
    
    # Execute all remaining steps
    while current_step < len(plan):
        step = plan[current_step]
        tool_name = step["tool"]
        
        try:
            # Get tool function
            tool_func = TOOLS.get(tool_name)
            if not tool_func:
                raise ValueError(f"Tool {tool_name} not found")
            
            # Prepare tool arguments based on state
            tool_args = prepare_tool_args(state, tool_name)
            
            # Execute tool
            logger.info("tool_executing", tool=tool_name, step=current_step)
            tool_result = tool_func(**tool_args)
            
            # Track tool usage
            tool_log = {
                "tool": tool_name,
                "step": current_step,
                "timestamp": datetime.now().isoformat(),
                "success": tool_result.get("success", False),
                "result": tool_result
            }
            state["tools_used"].append(tool_log)
            state["tool_results"][tool_name] = tool_result
            
            # Update state based on tool results
            update_state_from_tool(state, tool_name, tool_result)
            
            # Mark step as completed
            state["steps_completed"].append(step["step"])
            current_step += 1
            state["current_step"] = current_step
            
            log_step(state, "executor", {
                "tool": tool_name,
                "success": tool_result.get("success", False),
                "step_completed": step["step"]
            })
            
            logger.info("executor_step_completed", tool=tool_name, success=tool_result.get("success"))
            
            # If tool failed, stop execution (validator will handle recovery)
            if not tool_result.get("success", False):
                logger.warning("executor_tool_failed", tool=tool_name, stopping=True)
                break
            
        except Exception as e:
            logger.error("executor_error", tool=tool_name, error=str(e))
            state["error"] = f"Execution failed at {tool_name}: {str(e)}"
            state["tool_results"][tool_name] = {"success": False, "error": str(e)}
            break  # Stop on error, let validator handle
    
    logger.info("executor_finished", steps_completed=len(state["steps_completed"]), total_steps=len(plan))
    return state


def validator_node(state: AgentState) -> AgentState:
    """
    VALIDATOR NODE
    Agent validates execution results and decides if recovery is needed
    """
    logger.info("validator_started")
    
    validation_errors = []
    
    # Validate critical steps
    if not state.get("text"):
        validation_errors.append("No text extracted from document")
    
    if not state.get("sector"):
        validation_errors.append("Sector classification failed")
    
    if not state.get("events"):
        validation_errors.append("No events extracted")
    
    # Check tool failures
    failed_tools = [
        tool for tool in state.get("tools_used", [])
        if not tool.get("success", False)
    ]
    
    if failed_tools:
        validation_errors.append(f"Tools failed: {[t['tool'] for t in failed_tools]}")
    
    state["validation_errors"] = validation_errors
    state["validation_passed"] = len(validation_errors) == 0
    
    log_step(state, "validator", {
        "validation_passed": state["validation_passed"],
        "errors": validation_errors
    })
    
    logger.info("validator_completed", 
                passed=state["validation_passed"], 
                errors=len(validation_errors))
    
    return state


def recovery_node(state: AgentState) -> AgentState:
    """
    RECOVERY NODE
    Agent attempts to recover from failures
    """
    logger.info("recovery_started", retry_count=state.get("retry_count", 0))
    
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if retry_count >= max_retries:
        state["status"] = "failed"
        state["error"] = f"Max retries ({max_retries}) exceeded"
        logger.error("recovery_max_retries", retry_count=retry_count)
        return state
    
    state["retry_count"] = retry_count + 1
    
    # Recovery strategy: retry failed steps
    recovery_actions = []
    failed_tools = [
        tool for tool in state.get("tools_used", [])
        if not tool.get("success", False)
    ]
    
    for failed_tool in failed_tools:
        tool_name = failed_tool["tool"]
        recovery_actions.append(f"Retry {tool_name}")
        
        # Reset step to retry
        plan = state.get("plan", [])
        for i, step in enumerate(plan):
            if step["tool"] == tool_name:
                state["current_step"] = i
                break
    
    state["recovery_actions"] = recovery_actions
    
    log_step(state, "recovery", {
        "retry_count": state["retry_count"],
        "actions": recovery_actions
    })
    
    logger.info("recovery_completed", retry_count=state["retry_count"], actions=recovery_actions)
    
    return state


def should_continue(state: AgentState) -> Literal["continue", "end"]:
    """Decision: Should we continue or end?"""
    if state.get("validation_passed", False):
        state["status"] = "success"
        state["end_time"] = datetime.now()
        return "end"
    return "continue"


def should_retry(state: AgentState) -> Literal["retry", "fail"]:
    """Decision: Should we retry or fail?"""
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if retry_count < max_retries:
        return "retry"
    
    state["status"] = "failed"
    state["end_time"] = datetime.now()
    return "fail"


def prepare_tool_args(state: AgentState, tool_name: str) -> dict:
    """Prepare arguments for tool execution"""
    args = {}
    
    if tool_name == "preprocess_document":
        # File should already be uploaded in orchestrator
        args = {
            "file_id": state.get("file_id"),
            "file_bytes": state.get("file_bytes"),
            "filename": state.get("filename"),
            "stored_path": state.get("stored_path", state.get("file_id", ""))
        }
    elif tool_name == "classify_sector":
        args = {
            "text": state.get("text", ""),
            "metadata": state.get("metadata", {})
        }
    elif tool_name == "extract_events":
        args = {
            "sector": state.get("sector", ""),
            "text": state.get("text", ""),
            "metadata": state.get("metadata", {})
        }
    elif tool_name == "detect_risks":
        # Fetch timeline if not already in state
        timeline = state.get("timeline", [])
        if not timeline:
            from agent.tools import tool_get_timeline
            timeline_result = tool_get_timeline(state.get("entity_id"), limit=50)
            if timeline_result.get("success"):
                timeline = timeline_result.get("timeline", [])
                state["timeline"] = timeline
        
        args = {
            "sector": state.get("sector", ""),
            "events": state.get("events", []),
            "timeline": timeline
        }
    elif tool_name == "store_events":
        args = {
            "events": state.get("events", []),
            "entity_id": state.get("entity_id"),
            "file_id": state.get("file_id"),
            "sector": state.get("sector", "")
        }
    elif tool_name == "create_embeddings":
        args = {
            "events": state.get("events", []),
            "file_id": state.get("file_id"),
            "entity_id": state.get("entity_id"),
            "text": state.get("text", "")
        }
    elif tool_name == "generate_alerts":
        # Fetch timeline if not already in state
        timeline = state.get("timeline", [])
        if not timeline:
            from agent.tools import tool_get_timeline
            timeline_result = tool_get_timeline(state.get("entity_id"), limit=50)
            if timeline_result.get("success"):
                timeline = timeline_result.get("timeline", [])
                state["timeline"] = timeline
        
        args = {
            "risks": state.get("risks", []),
            "events": state.get("events", []),
            "timeline": timeline,
            "sector": state.get("sector", ""),
            "file_id": state.get("file_id")
        }
    elif tool_name == "store_alerts":
        args = {
            "alerts": state.get("alerts", []),
            "entity_id": state.get("entity_id")
        }
    elif tool_name == "get_timeline":
        args = {
            "entity_id": state.get("entity_id"),
            "limit": 50
        }
    elif tool_name == "generate_insights":
        args = {
            "events": state.get("events", []),
            "risks": state.get("risks", []),
            "alerts": state.get("alerts", []),
            "sector": state.get("sector", ""),
            "text": state.get("text", "")
        }
    
    return args


def update_state_from_tool(state: AgentState, tool_name: str, result: dict):
    """Update state based on tool results"""
    if not result.get("success"):
        return
    
    if tool_name == "preprocess_document":
        preprocess_result = result.get("result", {})
        state["text"] = preprocess_result.get("text", "")
        state["metadata"] = preprocess_result.get("metadata", {})
    
    elif tool_name == "classify_sector":
        classification = result.get("result", {})
        state["sector"] = classification.get("sector", "")
        state["confidence"] = classification.get("confidence", 0.0)
    
    elif tool_name == "extract_events":
        state["events"] = result.get("events", [])
    
    elif tool_name == "detect_risks":
        state["risks"] = result.get("risks", [])
    
    elif tool_name == "generate_alerts":
        state["alerts"] = result.get("alerts", [])
    
    elif tool_name == "get_timeline":
        state["timeline"] = result.get("timeline", [])
    
    elif tool_name == "generate_insights":
        state["insights"] = result.get("insights", {})

