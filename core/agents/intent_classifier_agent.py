from typing import Dict, Any, Optional
from groq import Groq
from core.agents.base_agent import BaseAgent
from config.settings import settings


class IntentClassifier(BaseAgent):
    """
    Classifies user query intent.

    OUTPUTS:
        - ANALYTICAL: Requires SQL (aggregations, filters, comparisons)
        - SEMANTIC: Requires vector search (trends, patterns, vague concepts)
        - HYBRID: Requires both approaches

    EXAMPLES:
        "top 10 customers by revenue" → ANALYTICAL
        "sales trends in western region" → SEMANTIC
        "delivery issues for high-value customers" → HYBRID
    """

    def __init__(self):
        super().__init__("intent_classifier")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)

    def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify query intent.

        Returns:
            dict: {
                "success": True,
                "result": {
                    "intent": "ANALYTICAL|SEMANTIC|HYBRID",
                    "confidence": float,
                    "reasoning": str
                },
                "metadata": {...}
            }
        """
        try:
            self.logger.info("classifying_intent", query=query)

            classification = self._classify(query, context)

            self.logger.info(
                "intent_classified",
                intent=classification["intent"],
                confidence=classification["confidence"],
            )

            return self._create_response(success=True, result=classification)

        except Exception as e:
            return self._handle_error(e, query)

    def _classify(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Use LLM to classify intent with conversation context."""
        from core.graphs.conversation_utils import format_conversation_context

        # Get conversation context if available
        conversation_context = ""
        if context and context.get("conversation_history"):
            conversation_context = format_conversation_context(
                context.get("conversation_history"),
                max_turns=3,  # Last 3 exchanges for intent classification
            )
            conversation_context = f"\n\n{conversation_context}\n"

        prompt = f"""You are an intent classifier for a SAP sales analytics chatbot.
        {conversation_context}
        CURRENT QUERY: {query}
        
        Classify this query into ONE of these categories:
        1. CHITCHAT - Casual conversation:
           - Greetings, thanks, goodbyes
           - Help requests, general questions about capabilities
           - Small talk
           Examples: "hi", "thank you", "what can you do?"
           
        2. ANALYTICAL - Requires precise SQL queries:
           - Aggregations (SUM, AVG, COUNT, MIN, MAX)
           - Top N rankings
           - Specific filters (dates, regions, customers)
           - Comparisons between groups
           Examples: "top 10 customers", "average order value", "sales in Q4"
           
        3. SEMANTIC - Requires semantic/vector search:
           - Vague or conceptual queries
           - Pattern recognition
           - Trends or insights
           - "Similar to" queries
           Examples: "sales trends", "delivery issues", "unusual orders"
           
        4. HYBRID - Requires both SQL and semantic search:
           - Combines precise metrics with vague concepts
           - "High-value customers with delivery problems"
           - "Top regions with declining trends"
        
        IMPORTANT: If there is conversation history, consider whether this is a follow-up question.
        Follow-up questions often reference previous context (e.g., "What about EAST district?" after asking about customers).
        
        Respond ONLY with valid JSON in this exact format:
        {{
            "intent": "CHITCHAT|ANALYTICAL|SEMANTIC|HYBRID",
            "confidence": 0.0-1.0,
            "reasoning": "Brief explanation"
        }}
        JSON Response:"""

        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        # Parse JSON response
        import json

        result_text = response.choices[0].message.content.strip()
        result_text = result_text.replace("```json", "").replace("```", "").strip()

        try:
            classification = json.loads(result_text)

            # Validate intent
            if classification["intent"] not in [
                "ANALYTICAL",
                "SEMANTIC",
                "HYBRID",
                "CHITCHAT",
            ]:
                self.logger.warning("invalid_intent", intent=classification["intent"])
                classification["intent"] = "ANALYTICAL"  # Default fallback

            return classification

        except json.JSONDecodeError as e:
            self.logger.error("json_parse_failed", text=result_text, error=str(e))
            # Fallback to ANALYTICAL for safety
            return {
                "intent": "ANALYTICAL",
                "confidence": 0.5,
                "reasoning": "Failed to parse LLM response, defaulting to SQL",
            }
