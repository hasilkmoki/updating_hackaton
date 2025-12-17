"""
LangGraph Agent Orchestration
Production-grade agent with Planner → Executor → Validator → Recovery loop
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv

from agent.state import AgentState
from agent.nodes import (
    planner_node,
    executor_node,
    validator_node,
    recovery_node,
    should_retry,
    should_continue
)
from config.logging import logger

load_dotenv()

# LLM will be initialized lazily when needed
llm = None

def get_llm():
    """Get LLM instance (lazy initialization)"""
    global llm
    if llm is not None:
        return llm
    
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
    
    try:
        if LLM_PROVIDER == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                temperature=0.1
            )
        else:
            # Try to import langchain-groq, but make it optional
            try:
                from langchain_groq import ChatGroq
                llm = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.1
                )
            except ImportError:
                logger.warning("langchain_groq_not_installed", 
                             hint="Install with: pip install langchain-groq")
                # Fallback: agent will work without LLM for planning
                llm = None
        if llm:
            logger.info("llm_initialized", provider=LLM_PROVIDER)
    except Exception as e:
        logger.warning("llm_init_failed", error=str(e), provider=LLM_PROVIDER)
        # Fallback to None - agent will work without LLM for planning
        llm = None
    
    return llm


def create_agent_graph():
    """Create the LangGraph agent workflow"""
    
    # Create state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes (agent states)
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("recovery", recovery_node)
    
    # Define edges (flow control)
    workflow.set_entry_point("planner")
    
    # Planner → Executor
    workflow.add_edge("planner", "executor")
    
    # Executor → Validator
    workflow.add_edge("executor", "validator")
    
    # Validator → Decision point
    workflow.add_conditional_edges(
        "validator",
        should_continue,  # Decision function
        {
            "continue": "recovery",  # If validation fails, go to recovery
            "end": END  # If validation passes, end
        }
    )
    
    # Recovery → Decision point
    workflow.add_conditional_edges(
        "recovery",
        should_retry,  # Decision function
        {
            "retry": "executor",  # Retry execution
            "fail": END  # Max retries reached, fail
        }
    )
    
    # Compile graph
    app = workflow.compile()
    
    logger.info("agent_graph_created", nodes=["planner", "executor", "validator", "recovery"])
    
    return app


# Global agent graph instance (lazy initialization)
agent_graph = None

def get_agent_graph():
    """Get agent graph instance (lazy initialization)"""
    global agent_graph
    if agent_graph is None:
        agent_graph = create_agent_graph()
    return agent_graph

