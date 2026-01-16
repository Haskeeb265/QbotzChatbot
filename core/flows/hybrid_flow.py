from typing import Dict, Any, List, Literal
from utility.observability.logger import get_logger

logger = get_logger("hybrid_flow")


class HybridExecutionFlow:
    """
    Executes both SQL and Vector search flows and intelligently merges results.

    Merging Strategy:
    1. SQL results get score based on rank (1/position)
    2. Vector results get score from similarity
    3. Combine with configurable weights (default: SQL=0.6, Vector=0.4)
    4. Deduplicate by sales_order
    5. Sort by combined score
    """

    def __init__(
        self, sql_flow, vector_flow, sql_weight: float = 0.6, vector_weight: float = 0.4
    ):
        self.sql_flow = sql_flow
        self.vector_flow = vector_flow
        self.sql_weight = sql_weight
        self.vector_weight = vector_weight
        self.logger = logger

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute hybrid search flow.

        Args:
            state: ChatbotState dictionary

        Returns:
            Updated state with hybrid_results and result_sources
        """
        self.logger.info("hybrid_flow_start", query=state["query"])

        # Run both flows
        self.logger.info("executing_sql_flow")
        state = self.sql_flow.run(state)

        self.logger.info("executing_vector_flow")
        state = self.vector_flow.run(state)

        # Extract results
        sql_results = state.get("sql_results", [])
        vector_results = state.get("vector_results", [])

        self.logger.info(
            "merging_results",
            sql_count=len(sql_results),
            vector_count=len(vector_results),
        )

        # Merge and rank results
        hybrid_results = self._merge_results(sql_results, vector_results)

        # Annotate sources
        result_sources = self._annotate_sources(hybrid_results)

        state["hybrid_results"] = hybrid_results
        state["result_sources"] = result_sources

        self.logger.info(
            "hybrid_flow_complete",
            hybrid_count=len(hybrid_results),
            sources=result_sources,
        )

        return state

    def _merge_results(
        self, sql_results: List[Dict[str, Any]], vector_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge SQL and Vector results with intelligent deduplication.

        Algorithm:
        1. Score SQL results by rank (1/position)
        2. Score Vector results by similarity
        3. Normalize both to 0-1 scale
        4. Combine scores with weights
        5. Deduplicate by sales_order (prefer SQL version, boost with vector similarity)
        6. Sort by combined score descending

        Args:
            sql_results: Results from SQL query
            vector_results: Results from vector search

        Returns:
            Merged and ranked results
        """
        merged_map: Dict[str, Dict[str, Any]] = {}

        # Process SQL results
        for rank, result in enumerate(sql_results, start=1):
            sales_order = result.get("sales_order")
            if not sales_order:
                continue

            # SQL score: inverse rank, normalized by max results
            sql_score = 1.0 / rank
            normalized_sql_score = sql_score * (1.0 / max(1, len(sql_results)))

            merged_map[sales_order] = {
                **result,  # Copy all SQL fields
                "source": "SQL",
                "sql_rank": rank,
                "sql_score": normalized_sql_score,
                "vector_similarity": None,
                "hybrid_score": normalized_sql_score * self.sql_weight,
            }

        # Process Vector results
        for result in vector_results:
            sales_order = result.get("sales_order")
            similarity = result.get("similarity", 0.0)

            if not sales_order:
                continue

            if sales_order in merged_map:
                # Deduplicate: Boost existing SQL result with vector similarity
                merged_map[sales_order]["source"] = "BOTH"
                merged_map[sales_order]["vector_similarity"] = similarity

                # Recalculate hybrid score with vector contribution
                sql_contribution = (
                    merged_map[sales_order]["sql_score"] * self.sql_weight
                )
                vector_contribution = similarity * self.vector_weight
                merged_map[sales_order]["hybrid_score"] = (
                    sql_contribution + vector_contribution
                )

            else:
                # New result from vector only
                merged_map[sales_order] = {
                    **result,  # Copy all vector fields
                    "source": "VECTOR",
                    "sql_rank": None,
                    "sql_score": None,
                    "vector_similarity": similarity,
                    "hybrid_score": similarity * self.vector_weight,
                }

        # Convert to list and sort by hybrid score
        merged_results = list(merged_map.values())
        merged_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        self.logger.info(
            "merge_complete",
            total_results=len(merged_results),
            sql_only=sum(1 for r in merged_results if r["source"] == "SQL"),
            vector_only=sum(1 for r in merged_results if r["source"] == "VECTOR"),
            both=sum(1 for r in merged_results if r["source"] == "BOTH"),
        )

        return merged_results

    def _annotate_sources(
        self, hybrid_results: List[Dict[str, Any]]
    ) -> Dict[str, Literal["SQL", "VECTOR", "BOTH"]]:
        """
        Create a mapping of sales_order -> source.

        Args:
            hybrid_results: Merged results

        Returns:
            Dictionary mapping sales_order to source type
        """
        return {
            result["sales_order"]: result["source"]
            for result in hybrid_results
            if "sales_order" in result
        }
