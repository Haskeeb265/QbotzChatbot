from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import END, StateGraph

from config.settings import settings
from core.agents.conversation_resolver_agent import ConversationResolverAgent
from core.agents.embedding_agent import EmbeddingAgent
from core.agents.intent_classifier_agent import IntentClassifier
from core.agents.sql_agent import SQLAgent
from core.agents.summarizer_agent import SummarizerAgent
from core.agents.vector_verifier_agent import VectorVerifier
from core.agents.visualization_agent import VisualizationAgent
from core.flows.chitchat_flow import ChitchatFlow
from core.flows.hybrid_flow import HybridExecutionFlow
from core.flows.sql_flow import SQLExecutionFlow
from core.flows.vector_flow import VectorExecutionFlow
from core.graphs.state import ChatbotState
from utility.observability.logger import get_logger

logger = get_logger("supervisor")


class SupervisorGraph:
    def __init__(self):
        self.conversation_resolver = ConversationResolverAgent()
        self.intent_classifier = IntentClassifier()
        self.sql_flow = SQLExecutionFlow(SQLAgent())
        self.vector_flow = VectorExecutionFlow(EmbeddingAgent(), VectorVerifier())
        self.hybrid_flow = HybridExecutionFlow(
            self.sql_flow,
            self.vector_flow,
            sql_weight=settings.HYBRID_SQL_WEIGHT,
            vector_weight=settings.HYBRID_VECTOR_WEIGHT,
        )
        self.chitchat_flow = ChitchatFlow()
        self.summarizer = SummarizerAgent()
        self.visualization_agent = VisualizationAgent()

        self.graph = self._build_graph()

    def _route(self, state: ChatbotState) -> str:
        """Route based on classified intent (handles uppercase from classifier)."""
        intent = state.get("intent", "").upper()

        # Map intent to node name
        intent_map = {
            "ANALYTICAL": "sql",
            "SEMANTIC": "vector",
            "HYBRID": "hybrid",
            "CHITCHAT": "chitchat",
        }

        return intent_map.get(intent, "chitchat")

    def _build_graph(self):
        workflow = StateGraph(ChatbotState)

        workflow.add_node("resolve_conversation", self._resolve_conversation)
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("sql_flow", self._sql_node)
        workflow.add_node("vector_flow", self._vector_node)
        workflow.add_node("hybrid_flow", self._hybrid_node)
        workflow.add_node("chitchat", self._chitchat_node)
        workflow.add_node("visualize", self._visualize)
        workflow.add_node("summarize", self._summarize)

        workflow.set_entry_point("resolve_conversation")

        workflow.add_edge("resolve_conversation", "classify_intent")
        workflow.add_conditional_edges(
            "classify_intent",
            self._route,
            {
                "sql": "sql_flow",
                "vector": "vector_flow",
                "hybrid": "hybrid_flow",
                "chitchat": "chitchat",
            },
        )
        workflow.add_edge("sql_flow", "visualize")
        workflow.add_edge("vector_flow", "visualize")
        workflow.add_edge("hybrid_flow", "visualize")
        workflow.add_edge("visualize", "summarize")
        workflow.add_edge("summarize", END)
        workflow.add_edge("chitchat", END)

        return workflow.compile()

    # -------- Nodes --------

    def _resolve_conversation(self, state: ChatbotState) -> ChatbotState:
        result = self.conversation_resolver.run(
            state["query"],
            {
                "conversation_history": state.get("conversation_history", []),
                "last_turn": state.get("last_turn_metadata"),
            },
        )

        if result.get("success"):
            state["conversation_resolution"] = result["result"]
            state["is_follow_up"] = result["result"]["is_follow_up"]

        return state

    def _classify_intent(self, state: ChatbotState) -> ChatbotState:
        result = self.intent_classifier.run(
            state["query"],
            {"conversation_resolution": state.get("conversation_resolution")},
        )

        if result.get("success"):
            state["intent"] = result["result"]["intent"]
            state["intent_confidence"] = result["result"]["confidence"]

        return state

    def _sql_node(self, state: ChatbotState) -> ChatbotState:
        return self.sql_flow.run(state)

    def _vector_node(self, state: ChatbotState) -> ChatbotState:
        return self.vector_flow.run(state)

    def _hybrid_node(self, state: ChatbotState) -> ChatbotState:
        return self.hybrid_flow.run(state)

    def _chitchat_node(self, state: ChatbotState) -> ChatbotState:
        return self.chitchat_flow.run(state)

    def _visualize(self, state: ChatbotState) -> ChatbotState:
        """Check if visualization is needed and generate config."""
        result = self.visualization_agent.run(
            state["query"],
            {
                "sql_results": state.get("sql_results")
                or state.get("vector_results")
                or state.get("hybrid_results"),
                "is_follow_up": state.get("is_follow_up"),
                "last_turn_metadata": state.get("last_turn_metadata"),
            },
        )

        if result.get("success"):
            state["should_visualize"] = result["result"]["should_visualize"]
            state["visualization_config"] = result["result"]["viz_config"]

        return state

    def _summarize(self, state: ChatbotState) -> ChatbotState:
        if state.get("error"):
            state["summary"] = f"Error: {state['error']}"
            return state

        result = self.summarizer.run(
            state["query"],
            {
                "sql_results": state.get("sql_results"),
                "vector_results": state.get("vector_results"),
            },
        )

        if result.get("success"):
            state["summary"] = result["result"]["summary"]

        return state

    # -------- Public API --------

    def run(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        last_turn_metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatbotState:
        """
        Run the chatbot workflow.

        Args:
            query: User's question
            conversation_history: Previous conversation turns
            last_turn_metadata: Metadata from previous turn

        Returns:
            Final state with summary
        """
        logger.info("supervisor_starting", query=query)

        # Initialize state with all required fields
        initial_state = ChatbotState(
            query=query,
            intent=None,
            intent_confidence=None,
            is_follow_up=None,
            sql=None,
            sql_results=None,
            last_sql_context=None,
            expanded_query=None,
            vector_results=None,
            vector_confidence=None,
            hybrid_results=None,
            result_sources=None,
            conversation_history=conversation_history or [],
            entities=None,
            should_visualize=None,
            visualization_config=None,
            summary=None,
            error=None,
        )

        # Add conversation resolution fields (not in TypedDict but used internally)
        initial_state["conversation_resolution"] = None  # type: ignore
        initial_state["last_turn_metadata"] = last_turn_metadata  # type: ignore

        # Execute graph
        final_state = self.graph.invoke(initial_state)

        logger.info(
            "supervisor_complete",
            intent=final_state.get("intent"),
            has_summary=bool(final_state.get("summary")),
            is_follow_up=final_state.get("is_follow_up"),
        )

        return final_state
