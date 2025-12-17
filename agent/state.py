"""
Agent State Definition
Manages state across the agent execution graph
"""
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class AgentState(TypedDict):
    """Core agent state that flows through the graph"""
    
    # Input
    file_bytes: bytes
    filename: str
    entity_id: str
    file_id: str
    
    # Processing
    text: str
    metadata: Dict[str, Any]
    sector: str
    confidence: float
    
    # Agent decisions
    plan: List[Dict[str, Any]]  # Agent's execution plan
    current_step: int
    steps_completed: List[str]
    
    # Execution results
    events: List[Dict[str, Any]]
    risks: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
    insights: Dict[str, Any]
    
    # Tool usage
    tools_used: List[Dict[str, Any]]  # Track all tool calls
    tool_results: Dict[str, Any]
    
    # Validation
    validation_passed: bool
    validation_errors: List[str]
    
    # Recovery
    retry_count: int
    max_retries: int
    recovery_actions: List[str]
    
    # Observability
    execution_log: List[Dict[str, Any]]  # Step-by-step logs
    start_time: datetime
    end_time: Optional[datetime]
    
    # Final outcome
    status: str  # "success", "failed", "retrying"
    error: Optional[str]
    final_result: Optional[Dict[str, Any]]

