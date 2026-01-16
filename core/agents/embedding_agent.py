from typing import Dict, Any, Optional
from groq import Groq
from core.agents.base_agent import BaseAgent
from config.settings import settings


class EmbeddingAgent(BaseAgent):
    """
    Expands user queries for better semantic search.

    Example:
        "delivery issues" → "delivery problems, shipping delays, blocked orders"
    """

    def __init__(self):
        super().__init__("embedding_agent")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)

    def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Expand query with related terms.

        Returns:
            dict: {
                "success": True,
                "result": {
                    "original_query": "delivery issues",
                    "expanded_query": "delivery problems, shipping delays, blocked orders, failed deliveries",
                    "expansion_count": 3
                }
            }
        """
        try:
            self.logger.info("expanding_query", query=query)

            expanded = self._expand_query(query, context)

            return self._create_response(
                success=True,
                result={
                    "original_query": query,
                    "expanded_query": expanded,
                    "expansion_count": len(expanded.split(",")),
                },
            )

        except Exception as e:
            return self._handle_error(e, query)

    def _expand_query(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Use LLM to generate related terms with conversation context."""
        from core.graphs.conversation_utils import format_conversation_context

        # Get conversation context if available
        conversation_context = ""
        if context and context.get("conversation_history"):
            conversation_context = format_conversation_context(
                context.get("conversation_history"), max_turns=2
            )
            conversation_context = f"\n{conversation_context}\n\n"

        prompt = f"""You are a query expansion assistant for SAP sales analytics.
        {conversation_context}
        Original query: "{query}"
        Generate 3-5 related terms or synonyms that would help find relevant sales orders.
        Focus on SAP sales concepts like:
        - Order status (completed, blocked, approved, pending)
        - Delivery issues (delays, problems, failures)
        - Financial terms (revenue, value, amount, payment)
        - Geographic terms (region, district, office)
        
        If there is conversation history, use it to better understand the context.
        For example, if previous query was about "customers" and current is "delivery issues",
        expand to include customer-related delivery terms.
        
        Return ONLY the expanded query as comma-separated terms.
        Do NOT include the original query.
        Do NOT add explanations.
        Format: "term1, term2, term3, term4"
        Expanded query:"""

        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        expanded = response.choices[0].message.content.strip()

        # Combine original + expanded
        return f"{query}, {expanded}"
