# agents/summarizer.py
from typing import Dict, Any, Optional, List
from groq import Groq
from core.agents.base_agent import BaseAgent
from config.settings import settings


class SummarizerAgent(BaseAgent):
    """
    Converts query results to natural language.

    Works for both SQL and vector search results.
    """

    def __init__(self):
        super().__init__("summarizer")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)

    def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate natural language summary.

        Args:
            query (str): Original user question.
            context (Optional[Dict[str, Any]]): Must contain either:
                - "sql_results": List of dicts from SQL query
                - "vector_results": List of dicts from vector search

        Returns:
            dict: {
                "success": True,
                "result": {
                    "summary": "Your top customer is 1700031827 with 20 billion SAR..."
                }
            }
        """
        try:
            if not context:
                return self._create_response(success=False, error="No context provided")

            # Get results from context (prioritize hybrid)
            hybrid_results = context.get("hybrid_results", [])
            sql_results = context.get("sql_results", [])
            vector_results = context.get("vector_results", [])

            if not hybrid_results and not sql_results and not vector_results:
                return self._create_response(
                    success=True, result={"summary": "No results found for your query."}
                )

            # Generate summary based on result type
            if hybrid_results:
                summary = self._summarize_hybrid_results(query, hybrid_results)
            elif sql_results:
                summary = self._summarize_sql_results(query, sql_results)
            else:
                summary = self._summarize_vector_results(query, vector_results)

            return self._create_response(success=True, result={"summary": summary})

        except Exception as e:
            return self._handle_error(e, query)

    def _summarize_sql_results(self, query: str, results: List[Dict]) -> str:
        """Summarize SQL query results."""
        results_text = self._format_results(results)

        prompt = f"""You are a helpful sales analytics assistant. 
User asked: "{query}"
Query returned {len(results)} results:
{results_text}
Provide a concise, natural language summary that:
1. Directly answers the user's question
2. Highlights key insights
3. Uses clear numbers with proper formatting (e.g., "20.02 billion SAR")
4. Keeps it under 3 sentences
Summary:"""

        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Slight creativity for natural language
        )

        return response.choices[0].message.content.strip()

    def _summarize_vector_results(self, query: str, results: List[Dict]) -> str:
        """Summarize vector search results."""
        results_text = self._format_results(results)

        prompt = f"""You are a helpful sales analytics assistant.
User asked: "{query}"
Semantic search found {len(results)} relevant orders:
{results_text}
Provide a concise summary that:
1. Explains what patterns or trends were found
2. Highlights the most relevant findings
3. Mentions similarity confidence if available
4. Keeps it under 3 sentences
Summary:"""

        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    def _summarize_hybrid_results(self, query: str, results: List[Dict]) -> str:
        """Summarize hybrid search results (SQL + Vector combined)."""
        results_text = self._format_hybrid_results(results)

        # Count source breakdown
        sql_only = sum(1 for r in results if r.get("source") == "SQL")
        vector_only = sum(1 for r in results if r.get("source") == "VECTOR")
        both = sum(1 for r in results if r.get("source") == "BOTH")

        prompt = f"""You are a helpful sales analytics assistant.
User asked: "{query}"

Hybrid search (combining SQL and Vector search) found {len(results)} results:
- {sql_only} from structured SQL queries
- {vector_only} from semantic vector search  
- {both} matched by BOTH methods (highest confidence)

Results:
{results_text}

Provide a concise summary that:
1. Directly answers the user's question
2. Highlights results found by both methods (these are most relevant)
3. Mentions insights from both precise metrics (SQL) and patterns (Vector)
4. Uses clear numbers with proper formatting
5. Keeps it under 4 sentences

Summary:"""

        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    def _format_results(self, results: List[Dict]) -> str:
        """Format results for LLM consumption."""
        # Show max 10 results to avoid token limits
        results_to_show = results[:10]
        formatted = []

        for i, row in enumerate(results_to_show, 1):
            # Convert dict to readable format
            row_str = ", ".join([f"{k}: {v}" for k, v in row.items()])
            formatted.append(f"{i}. {row_str}")

        if len(results) > 10:
            formatted.append(f"... and {len(results) - 10} more results")

        return "\n".join(formatted)

    def _format_hybrid_results(self, results: List[Dict]) -> str:
        """Format hybrid results with source information."""
        # Show max 10 results to avoid token limits
        results_to_show = results[:10]
        formatted = []

        for i, row in enumerate(results_to_show, 1):
            # Extract source and score information
            source = row.get("source", "UNKNOWN")
            hybrid_score = row.get("hybrid_score", 0.0)

            # Create a clean version without internal metadata
            clean_row = {
                k: v
                for k, v in row.items()
                if k
                not in [
                    "source",
                    "sql_rank",
                    "sql_score",
                    "vector_similarity",
                    "hybrid_score",
                    "similarity",
                ]
            }

            # Add source indicator
            source_indicator = {
                "SQL": "[SQL]",
                "VECTOR": "[Vector]",
                "BOTH": "[SQL+Vector ★]",  # Star indicates high confidence
            }.get(source, "")

            row_str = ", ".join([f"{k}: {v}" for k, v in clean_row.items()])
            formatted.append(
                f"{i}. {source_indicator} {row_str} (score: {hybrid_score:.3f})"
            )

        if len(results) > 10:
            formatted.append(f"... and {len(results) - 10} more results")

        return "\n".join(formatted)
