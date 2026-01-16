from typing import Dict, Any
from core.tools import vector_search
from utility.observability.logger import get_logger

logger = get_logger("vector_flow")


class VectorExecutionFlow:
    """
    Handles semantic query expansion, vector search, and verification.
    """

    def __init__(self, embedding_agent, vector_verifier):
        self.embedding_agent = embedding_agent
        self.vector_verifier = vector_verifier

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("vector_flow_start", query=state["query"])

        context = {
            "conversation_history": state.get("conversation_history", []),
            "conversation_resolution": state.get("conversation_resolution"),
        }

        expansion = self.embedding_agent.run(state["query"], context)

        if not expansion["success"]:
            state["error"] = expansion["error"]
            return state

        expanded_query = expansion["result"]["expanded_query"]
        state["expanded_query"] = expanded_query

        vector_results = vector_search(expanded_query, limit=10)
        state["vector_results"] = vector_results

        verification = self.vector_verifier.run(
            state["query"], {"vector_results": vector_results}
        )

        if verification["success"]:
            state["vector_confidence"] = verification["result"]["confidence"]

        return state
