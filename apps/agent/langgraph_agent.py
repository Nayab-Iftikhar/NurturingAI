import logging
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END

from apps.agent.tools.text_to_sql import TextToSQLTool
from apps.agent.tools.document_rag import DocumentRAGTool
from services.llm_utils import get_llm_candidates

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the LangGraph agent"""
    query: str
    project_name: str
    tool_choice: Literal["text_to_sql", "document_rag", None]
    result: dict
    response: str


class RealEstateAgent:
    """LangGraph agent that routes between Text-to-SQL and Document RAG"""
    
    def __init__(self):
        # Initialize tools
        self.text_to_sql_tool = TextToSQLTool()
        self.document_rag_tool = DocumentRAGTool()
        
        # Initialize LLM for routing with fallback
        candidates = get_llm_candidates(temperature=0.3)
        if not candidates:
            raise RuntimeError(
                "No LLM providers configured. Please set OPENAI_API_KEY or ensure Ollama is running."
            )
        self.routing_provider, self.llm = candidates[0]
        logger.info("LangGraph agent routing LLM initialized with provider: %s", self.routing_provider)
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("route", self._route_query)
        workflow.add_node("text_to_sql", self._execute_text_to_sql)
        workflow.add_node("document_rag", self._execute_document_rag)
        workflow.add_node("synthesize", self._synthesize_response)
        
        # Set entry point
        workflow.set_entry_point("route")
        
        # Add edges
        workflow.add_conditional_edges(
            "route",
            self._should_use_sql,
            {
                "text_to_sql": "text_to_sql",
                "document_rag": "document_rag"
            }
        )
        
        workflow.add_edge("text_to_sql", "synthesize")
        workflow.add_edge("document_rag", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    def _route_query(self, state: AgentState) -> AgentState:
        """Route the query to determine which tool to use"""
        query = state["query"]
        project_name = state.get("project_name", "")
        
        # Use LLM to determine if query is about database/data or brochures
        routing_prompt = f"""Analyze this query and determine if it should use:
1. Text-to-SQL: Questions about data, statistics, counts, lists of leads, campaign data, database queries
2. Document RAG: Questions about property features, amenities, facilities, project details, brochures, specifications

Query: "{query}"
Project: {project_name}

Respond with ONLY "sql" or "rag" (no quotes, no explanation)."""
        
        try:
            response = self.llm.invoke(routing_prompt)
            tool_choice = response.content.strip().lower()
            
            if "sql" in tool_choice:
                state["tool_choice"] = "text_to_sql"
            else:
                state["tool_choice"] = "document_rag"
        except Exception as exc:
            # Default to RAG if routing fails
            logger.warning("Routing LLM failed, defaulting to document_rag: %s", exc)
            state["tool_choice"] = "document_rag"
        
        return state
    
    def _should_use_sql(self, state: AgentState) -> str:
        """Conditional edge function"""
        return state.get("tool_choice", "document_rag")
    
    def _execute_text_to_sql(self, state: AgentState) -> AgentState:
        """Execute Text-to-SQL tool"""
        result = self.text_to_sql_tool.execute(
            query=state["query"],
            project_name=state.get("project_name")
        )
        state["result"] = result
        return state
    
    def _execute_document_rag(self, state: AgentState) -> AgentState:
        """Execute Document RAG tool"""
        result = self.document_rag_tool.execute(
            query=state["query"],
            project_name=state.get("project_name")
        )
        state["result"] = result
        return state
    
    def _synthesize_response(self, state: AgentState) -> AgentState:
        """Synthesize final response"""
        result = state.get("result", {})
        
        if "error" in result:
            state["response"] = f"I encountered an error: {result['error']}. Please try rephrasing your question."
        elif "response" in result:
            state["response"] = result["response"]
        else:
            state["response"] = "I couldn't process your query. Please try again."
        
        return state
    
    def query(self, query: str, project_name: str = "") -> dict:
        """
        Execute a query through the agent
        
        Args:
            query: Natural language query
            project_name: Optional project name for context
            
        Returns:
            Dict with 'response', 'tool_used', and 'result' keys
        """
        initial_state = {
            "query": query,
            "project_name": project_name,
            "tool_choice": None,
            "result": {},
            "response": ""
        }
        
        final_state = self.graph.invoke(initial_state)
        
        return {
            "response": final_state["response"],
            "tool_used": final_state.get("tool_choice", "document_rag"),
            "result": final_state.get("result", {})
        }


# Global agent instance (lazy initialization)
_agent_instance = None


def get_agent():
    """Get or create agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RealEstateAgent()
    return _agent_instance

