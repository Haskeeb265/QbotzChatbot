from typing import Dict, Any


class ChitchatFlow:
    """
    Handles casual conversation responses.
    """

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["query"].lower().strip()

        if any(g in query for g in ["hi", "hello", "hey"]):
            state["summary"] = (
                "Hello! I'm your SAP Sales Analytics assistant. "
                "Ask me about customers, revenue, regions, or trends."
            )

        elif any(t in query for t in ["thank", "thanks"]):
            state["summary"] = "You're welcome. Happy to help."

        elif any(b in query for b in ["bye", "goodbye"]):
            state["summary"] = "Goodbye. Come back anytime you need insights."

        elif "help" in query:
            state["summary"] = (
                "I analyze SAP sales data. "
                "Try: 'Top customers by revenue' or 'Sales in WEST district'."
            )

        else:
            state["summary"] = (
                "I'm here to help with sales analytics. "
                "Ask me about customers, revenue, or orders."
            )

        return state
