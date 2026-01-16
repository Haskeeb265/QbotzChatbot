from typing import Dict, Any, Optional, List
import statistics
from core.agents.base_agent import BaseAgent
from utility.observability.logger import get_logger


class VectorVerifier(BaseAgent):
    """
    Verifies vector search result quality using statistical analysis.

    Returns confidence level (HIGH/MEDIUM/LOW) based on:
    - Average similarity score
    - Result count
    - Similarity variance (consistency)
    - Query specificity
    """

    def __init__(self):
        super().__init__("vector_verifier")

    def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verify vector search results and assign confidence level.

        Args:
            query: User's search query
            context: Must contain "vector_results" key

        Returns:
            dict: {
                "success": True,
                "result": {
                    "confidence": "HIGH|MEDIUM|LOW",
                    "avg_similarity": float,
                    "min_similarity": float,
                    "max_similarity": float,
                    "variance": float,
                    "result_count": int,
                    "query_length": int,
                    "reasoning": str
                }
            }
        """
        try:
            if not context or "vector_results" not in context:
                return self._create_response(
                    success=False, error="No vector results provided"
                )

            vector_results = context["vector_results"]

            if not vector_results:
                return self._create_response(
                    success=True,
                    result={
                        "confidence": "LOW",
                        "avg_similarity": 0.0,
                        "min_similarity": 0.0,
                        "max_similarity": 0.0,
                        "variance": 0.0,
                        "result_count": 0,
                        "query_length": len(query.split()),
                        "reasoning": "No vector matches found",
                    },
                )

            # Extract similarity scores
            similarities = [r.get("similarity", 0.0) for r in vector_results]
            result_count = len(similarities)

            # Calculate statistics
            avg_similarity = statistics.mean(similarities)
            min_similarity = min(similarities)
            max_similarity = max(similarities)

            # Calculate variance only if we have multiple results
            variance = statistics.variance(similarities) if result_count > 1 else 0.0

            # Query characteristics
            query_length = len(query.split())

            # Determine confidence level
            confidence, reasoning = self._calculate_confidence(
                avg_similarity=avg_similarity,
                min_similarity=min_similarity,
                max_similarity=max_similarity,
                variance=variance,
                result_count=result_count,
                query_length=query_length,
            )

            self.logger.info(
                "vector_verification_complete",
                confidence=confidence,
                avg_similarity=round(avg_similarity, 3),
                variance=round(variance, 4),
                result_count=result_count,
            )

            return self._create_response(
                success=True,
                result={
                    "confidence": confidence,
                    "avg_similarity": round(avg_similarity, 3),
                    "min_similarity": round(min_similarity, 3),
                    "max_similarity": round(max_similarity, 3),
                    "variance": round(variance, 4),
                    "result_count": result_count,
                    "query_length": query_length,
                    "reasoning": reasoning,
                },
            )

        except Exception as e:
            return self._handle_error(e, query)

    def _calculate_confidence(
        self,
        avg_similarity: float,
        min_similarity: float,
        max_similarity: float,
        variance: float,
        result_count: int,
        query_length: int,
    ) -> tuple[str, str]:
        """
        Calculate confidence level based on multiple factors.

        HIGH Confidence Criteria:
        - Average similarity ≥ 0.75
        - At least 3 results
        - Low variance (< 0.05) indicating consistent matches
        - Minimum similarity ≥ 0.65

        LOW Confidence Criteria:
        - Average similarity < 0.50
        - Fewer than 2 results
        - High variance (> 0.15) indicating inconsistent matches

        MEDIUM: Everything else

        Returns:
            tuple: (confidence_level, reasoning)
        """

        # HIGH confidence: Strong, consistent matches
        if (
            avg_similarity >= 0.75
            and result_count >= 3
            and variance < 0.05
            and min_similarity >= 0.65
        ):
            return "HIGH", (
                f"Strong matches: avg={avg_similarity:.2f}, "
                f"{result_count} results with low variance ({variance:.4f})"
            )

        # Also HIGH if exceptional average even with fewer results
        if avg_similarity >= 0.85 and result_count >= 2:
            return "HIGH", (
                f"Exceptional similarity: avg={avg_similarity:.2f} "
                f"with {result_count} results"
            )

        # LOW confidence: Weak or inconsistent matches
        if avg_similarity < 0.50:
            return "LOW", (
                f"Low average similarity ({avg_similarity:.2f}), "
                "results may not be relevant"
            )

        if result_count < 2:
            return "LOW", (
                f"Insufficient results ({result_count}), "
                f"avg similarity={avg_similarity:.2f}"
            )

        if variance > 0.15 and result_count >= 3:
            return "LOW", (
                f"High variance ({variance:.4f}) indicates inconsistent matches, "
                f"avg={avg_similarity:.2f}"
            )

        # MEDIUM confidence: Acceptable but not strong
        return "MEDIUM", (
            f"Acceptable matches: avg={avg_similarity:.2f}, "
            f"{result_count} results, variance={variance:.4f}"
        )
