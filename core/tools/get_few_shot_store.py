"""
Few-Shot SQL Examples Store
Stores example queries with embeddings for similarity-based retrieval

Refactored to use existing EmbeddingModelManager singleton infrastructure
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from core.storage.embedding.embedding_manager import EmbeddingModelManager
from utility.observability.logger import get_logger

logger = get_logger("few_shot_sql_store")


@dataclass
class SQLExample:
    """A single few-shot SQL example"""

    category: str
    question: str
    sql: str
    notes: Optional[str] = None
    difficulty: str = "medium"  # easy, medium, hard
    embedding: Optional[np.ndarray] = None


class FewShotSQLStore:
    """
    Manages few-shot SQL examples with vector similarity search.
    Uses the singleton EmbeddingModelManager for efficient embedding computation.

    Usage:
        store = FewShotSQLStore()
        examples = store.find_similar_examples("Which regions have declining sales?", top_k=2)
    """

    def __init__(self):
        logger.info("few_shot_store_initializing")

        # Get singleton embedding model instance (no reload!)
        self.embedding_model = EmbeddingModelManager.get_instance()
        self.examples: List[SQLExample] = []

        # Load examples first
        self._load_examples()

        # Compute embeddings for all examples using batch encoding
        self._compute_embeddings()

        logger.info(
            "few_shot_store_initialized",
            total_examples=len(self.examples),
            categories=len(self.get_all_categories()),
        )

    def _load_examples(self):
        """Load all few-shot examples"""

        logger.info("loading_few_shot_examples")

        # ============================================================
        # STRATEGIC SALES PERFORMANCE
        # ============================================================

        self.examples.append(
            SQLExample(
                category="Strategic Sales Performance",
                question="How is total net sales trending over time by billing date (monthly)?",
                sql="""SELECT
    DATE_TRUNC('month', billing_document_date) AS month,
    SUM(total_net_amount) AS total_net_sales
FROM sales_orders
WHERE billing_document_date IS NOT NULL
GROUP BY DATE_TRUNC('month', billing_document_date)
ORDER BY month;""",
                notes="Use DATE_TRUNC for time-based aggregation. Always filter NULL dates.",
                difficulty="easy",
            )
        )

        self.examples.append(
            SQLExample(
                category="Strategic Sales Performance",
                question="How is total net sales trending over time by billing date (quarterly)?",
                sql="""SELECT
    DATE_TRUNC('quarter', billing_document_date) AS quarter,
    SUM(total_net_amount) AS total_net_sales
FROM sales_orders
WHERE billing_document_date IS NOT NULL
GROUP BY DATE_TRUNC('quarter', billing_document_date)
ORDER BY quarter;""",
                notes="Use DATE_TRUNC with 'quarter' for quarterly aggregation. Filter NULL dates.",
                difficulty="easy",
            )
        )

        self.examples.append(
            SQLExample(
                category="Strategic Sales Performance",
                question="Which sales regions are generating the highest and lowest net revenue?",
                sql="""(SELECT
    sales_district,
    SUM(total_net_amount) AS total_net_revenue
FROM sales_orders
WHERE sales_district IS NOT NULL
GROUP BY sales_district
ORDER BY total_net_revenue DESC
LIMIT 1)
UNION ALL
(SELECT
    sales_district,
    SUM(total_net_amount) AS total_net_revenue
FROM sales_orders
WHERE sales_district IS NOT NULL
GROUP BY sales_district
ORDER BY total_net_revenue ASC
LIMIT 1);""",
                notes="CRITICAL: UNION with ORDER BY/LIMIT requires parentheses around each SELECT. Use sales_district for regions.",
                difficulty="medium",
            )
        )

        self.examples.append(
            SQLExample(
                category="Strategic Sales Performance",
                question="Which sales organizations contribute most to overall revenue?",
                sql="""SELECT
    sales_organization,
    SUM(total_net_amount) AS total_net_revenue
FROM sales_orders
WHERE sales_organization IS NOT NULL
GROUP BY sales_organization
ORDER BY total_net_revenue DESC;""",
                notes="Always filter NULL values for cleaner results",
                difficulty="easy",
            )
        )

        self.examples.append(
            SQLExample(
                category="Strategic Sales Performance",
                question="What are the top 5 and bottom 5 sales districts by revenue?",
                sql="""(SELECT
    sales_district,
    SUM(total_net_amount) AS total_net_revenue,
    'Top 5' AS category
FROM sales_orders
WHERE sales_district IS NOT NULL
GROUP BY sales_district
ORDER BY total_net_revenue DESC
LIMIT 5)
UNION ALL
(SELECT
    sales_district,
    SUM(total_net_amount) AS total_net_revenue,
    'Bottom 5' AS category
FROM sales_orders
WHERE sales_district IS NOT NULL
GROUP BY sales_district
ORDER BY total_net_revenue ASC
LIMIT 5)
ORDER BY total_net_revenue DESC;""",
                notes="UNION queries with ORDER BY/LIMIT must wrap each SELECT in parentheses. Can add ORDER BY after UNION.",
                difficulty="medium",
            )
        )

        # ============================================================
        # BILLING & PRODUCT MIX INSIGHTS
        # ============================================================

        self.examples.append(
            SQLExample(
                category="Billing & Product Mix",
                question="Which billing types generate the highest net value and which are declining?",
                sql="""SELECT
    sales_order_type,
    DATE_TRUNC('month', billing_document_date) AS month,
    SUM(total_net_amount) AS total_net_value
FROM sales_orders
WHERE billing_document_date IS NOT NULL
  AND sales_order_type IS NOT NULL
GROUP BY sales_order_type, DATE_TRUNC('month', billing_document_date)
ORDER BY sales_order_type, month;""",
                notes="Time-series by type to identify trends and declines. Always use DATE_TRUNC in GROUP BY too.",
                difficulty="medium",
            )
        )

        self.examples.append(
            SQLExample(
                category="Billing & Product Mix",
                question="What is the average net value per sales document by billing type?",
                sql="""SELECT
    sales_order_type,
    AVG(total_net_amount) AS avg_net_value_per_document,
    COUNT(sales_order) AS document_count
FROM sales_orders
WHERE sales_order_type IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY sales_order_type
ORDER BY avg_net_value_per_document DESC;""",
                notes="Include count for context. Filter NULL values.",
                difficulty="easy",
            )
        )

        self.examples.append(
            SQLExample(
                category="Billing & Product Mix",
                question="Are certain billing types concentrated in specific regions or channels?",
                sql="""SELECT
    sales_organization AS region,
    distribution_channel AS channel,
    sales_order_type AS billing_type,
    COUNT(*) AS order_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (
            PARTITION BY sales_organization, distribution_channel
        ),
        2
    ) AS share_percentage
FROM sales_orders
WHERE overall_sd_process_status NOT IN ('CANCELLED', 'REJECTED')
  AND sales_order_date IS NOT NULL
  AND sales_organization IS NOT NULL
  AND distribution_channel IS NOT NULL
  AND sales_order_type IS NOT NULL
GROUP BY sales_organization, distribution_channel, sales_order_type
ORDER BY region, channel, share_percentage DESC;""",
                notes="Use window functions for share calculations. Filter out cancelled orders. Use ROUND for percentages.",
                difficulty="hard",
            )
        )

        # ============================================================
        # CUSTOMER & PARTNER ANALYSIS
        # ============================================================

        self.examples.append(
            SQLExample(
                category="Customer & Partner Analysis",
                question="Who are the top customers by total net value?",
                sql="""SELECT
    sold_to_party,
    SUM(total_net_amount) AS total_net_value,
    COUNT(sales_order) AS order_count
FROM sales_orders
WHERE sold_to_party IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY sold_to_party
ORDER BY total_net_value DESC
LIMIT 10;""",
                notes="Use sold_to_party for customer, not 'customer_name'. Include order count.",
                difficulty="easy",
            )
        )

        self.examples.append(
            SQLExample(
                category="Customer & Partner Analysis",
                question="What is the average deal size per customer across regions?",
                sql="""SELECT
    sold_to_party,
    sales_district,
    AVG(total_net_amount) AS avg_deal_size,
    COUNT(sales_order) AS deal_count
FROM sales_orders
WHERE sold_to_party IS NOT NULL
  AND sales_district IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY sold_to_party, sales_district
HAVING COUNT(sales_order) >= 3
ORDER BY avg_deal_size DESC;""",
                notes="Filter for customers with minimum activity using HAVING. Include deal count.",
                difficulty="medium",
            )
        )

        self.examples.append(
            SQLExample(
                category="Customer & Partner Analysis",
                question="Which customers have the highest and lowest average order values?",
                sql="""(SELECT
    sold_to_party,
    AVG(total_net_amount) AS avg_order_value,
    COUNT(sales_order) AS order_count,
    'Highest' AS category
FROM sales_orders
WHERE sold_to_party IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY sold_to_party
HAVING COUNT(sales_order) >= 5
ORDER BY avg_order_value DESC
LIMIT 10)
UNION ALL
(SELECT
    sold_to_party,
    AVG(total_net_amount) AS avg_order_value,
    COUNT(sales_order) AS order_count,
    'Lowest' AS category
FROM sales_orders
WHERE sold_to_party IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY sold_to_party
HAVING COUNT(sales_order) >= 5
ORDER BY avg_order_value ASC
LIMIT 10);""",
                notes="UNION with ORDER BY requires parentheses. Use HAVING for minimum activity threshold.",
                difficulty="medium",
            )
        )

        # ============================================================
        # CHANNEL & DIVISION PERFORMANCE
        # ============================================================

        self.examples.append(
            SQLExample(
                category="Channel & Division Performance",
                question="Which distribution channels deliver the highest sales volume and revenue?",
                sql="""SELECT
    distribution_channel,
    COUNT(sales_order) AS sales_document_count,
    SUM(total_net_amount) AS total_net_revenue,
    AVG(total_net_amount) AS avg_revenue_per_order
FROM sales_orders
WHERE distribution_channel IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY distribution_channel
ORDER BY total_net_revenue DESC;""",
                notes="Use distribution_channel, not 'sales_channel' or 'channel'. Include average for context.",
                difficulty="easy",
            )
        )

        self.examples.append(
            SQLExample(
                category="Channel & Division Performance",
                question="How does revenue performance vary across divisions?",
                sql="""SELECT
    organization_division,
    SUM(total_net_amount) AS total_net_revenue,
    COUNT(sales_order) AS order_count,
    AVG(total_net_amount) AS avg_order_value
FROM sales_orders
WHERE organization_division IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY organization_division
ORDER BY total_net_revenue DESC;""",
                notes="Use organization_division, not just 'division'. Include multiple metrics.",
                difficulty="easy",
            )
        )

        self.examples.append(
            SQLExample(
                category="Channel & Division Performance",
                question="Which division has the highest average net value per sales document?",
                sql="""SELECT
    organization_division,
    AVG(total_net_amount) AS avg_net_value_per_document,
    COUNT(sales_order) AS document_count,
    SUM(total_net_amount) AS total_revenue
FROM sales_orders
WHERE organization_division IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY organization_division
ORDER BY avg_net_value_per_document DESC;""",
                notes="Include both average and totals for complete picture.",
                difficulty="easy",
            )
        )

        # ============================================================
        # RISK & OPPORTUNITY DETECTION
        # ============================================================

        self.examples.append(
            SQLExample(
                category="Risk & Opportunity Detection",
                question="Are there regions or customers with high sales document counts but low average net value?",
                sql="""WITH overall_avg AS (
    SELECT AVG(total_net_amount) AS avg_value
    FROM sales_orders
    WHERE total_net_amount IS NOT NULL
)
SELECT
    sales_district,
    sold_to_party,
    COUNT(sales_order) AS document_count,
    AVG(total_net_amount) AS avg_net_value,
    (SELECT avg_value FROM overall_avg) AS overall_avg_value
FROM sales_orders
WHERE sales_district IS NOT NULL
  AND sold_to_party IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY sales_district, sold_to_party
HAVING COUNT(sales_order) > 50
   AND AVG(total_net_amount) < (SELECT avg_value FROM overall_avg)
ORDER BY document_count DESC;""",
                notes="Use CTEs for clarity. Compare against overall average. Filter for significance.",
                difficulty="hard",
            )
        )

        self.examples.append(
            SQLExample(
                category="Risk & Opportunity Detection",
                question="Which regions show declining sales despite high historical performance?",
                sql="""WITH monthly_sales AS (
    SELECT
        sales_district,
        DATE_TRUNC('month', billing_document_date) AS month,
        SUM(total_net_amount) AS monthly_net_sales
    FROM sales_orders
    WHERE sales_district IS NOT NULL
      AND billing_document_date IS NOT NULL
      AND total_net_amount IS NOT NULL
    GROUP BY sales_district, DATE_TRUNC('month', billing_document_date)
)
SELECT
    sales_district,
    month,
    monthly_net_sales,
    LAG(monthly_net_sales) OVER (
        PARTITION BY sales_district
        ORDER BY month
    ) AS prev_month_sales,
    monthly_net_sales - LAG(monthly_net_sales) OVER (
        PARTITION BY sales_district
        ORDER BY month
    ) AS month_over_month_change
FROM monthly_sales
ORDER BY sales_district, month;""",
                notes="Use CTEs for complex trend analysis. Use LAG() for month-over-month comparison.",
                difficulty="hard",
            )
        )

        self.examples.append(
            SQLExample(
                category="Risk & Opportunity Detection",
                question="Where can we increase revenue by focusing on high-value customers or channels?",
                sql="""WITH overall_avg AS (
    SELECT AVG(total_net_amount) AS avg_deal_size
    FROM sales_orders
    WHERE total_net_amount IS NOT NULL
)
SELECT
    distribution_channel,
    sold_to_party,
    SUM(total_net_amount) AS total_net_revenue,
    AVG(total_net_amount) AS avg_deal_size,
    COUNT(sales_order) AS order_count,
    (SELECT avg_deal_size FROM overall_avg) AS overall_avg
FROM sales_orders
WHERE distribution_channel IS NOT NULL
  AND sold_to_party IS NOT NULL
  AND total_net_amount IS NOT NULL
GROUP BY distribution_channel, sold_to_party
HAVING AVG(total_net_amount) > (SELECT avg_deal_size FROM overall_avg)
   AND COUNT(sales_order) >= 5
ORDER BY total_net_revenue DESC;""",
                notes="Use CTE with HAVING to filter for above-average performers with sufficient volume.",
                difficulty="hard",
            )
        )

        # ============================================================
        # TIME-BASED ANALYSIS (DATE FUNCTIONS)
        # ============================================================

        self.examples.append(
            SQLExample(
                category="Time-Based Analysis",
                question="What is the year-over-year revenue growth by month?",
                sql="""WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', sales_order_date) AS month,
        EXTRACT(YEAR FROM sales_order_date) AS year,
        EXTRACT(MONTH FROM sales_order_date) AS month_num,
        SUM(total_net_amount) AS monthly_revenue
    FROM sales_orders
    WHERE sales_order_date IS NOT NULL
      AND total_net_amount IS NOT NULL
    GROUP BY DATE_TRUNC('month', sales_order_date),
             EXTRACT(YEAR FROM sales_order_date),
             EXTRACT(MONTH FROM sales_order_date)
)
SELECT
    year,
    month_num,
    monthly_revenue,
    LAG(monthly_revenue) OVER (
        PARTITION BY month_num
        ORDER BY year
    ) AS prev_year_same_month,
    ROUND(
        (monthly_revenue - LAG(monthly_revenue) OVER (
            PARTITION BY month_num ORDER BY year
        )) * 100.0 / NULLIF(LAG(monthly_revenue) OVER (
            PARTITION BY month_num ORDER BY year
        ), 0),
        2
    ) AS yoy_growth_percent
FROM monthly_revenue
ORDER BY year, month_num;""",
                notes="Use EXTRACT for year/month. LAG with PARTITION BY month for YoY. Use NULLIF to avoid division by zero.",
                difficulty="hard",
            )
        )

        logger.info("few_shot_examples_loaded", count=len(self.examples))

    def _compute_embeddings(self):
        """
        Compute embeddings for all example questions using batch encoding.
        Uses the singleton embedding model for efficiency.
        """
        logger.info("computing_few_shot_embeddings", count=len(self.examples))

        # Extract all questions for batch encoding
        questions = [example.question for example in self.examples]

        # Use batch encoding for efficiency (all at once with progress bar)
        embeddings_list = self.embedding_model.encode_batch(questions)

        # Convert to numpy arrays and assign to examples
        for example, embedding in zip(self.examples, embeddings_list):
            example.embedding = np.array(embedding)

        logger.info("few_shot_embeddings_computed", count=len(self.examples))

    def find_similar_examples(
        self,
        query: str,
        top_k: int = 2,
        min_similarity: Optional[float] = None,
        category_filter: Optional[str] = None,
    ) -> List[SQLExample]:
        """
        Find most similar examples to the given query using cosine similarity.

        Args:
            query: User's natural language query
            top_k: Number of examples to return
            min_similarity: Minimum similarity threshold (0-1)
            category_filter: Filter by category

        Returns:
            List of most similar SQLExample objects
        """
        # Encode the query using singleton model
        query_embedding = np.array(self.embedding_model.encode_single(query))

        # Filter examples if needed
        candidates = self.examples
        if category_filter:
            candidates = [e for e in candidates if e.category == category_filter]

        # Calculate cosine similarity for all candidates
        similarities = []
        for example in candidates:
            similarity = np.dot(query_embedding, example.embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(example.embedding)
            )

            # Apply minimum similarity threshold if specified
            if min_similarity is None or similarity >= min_similarity:
                similarities.append((similarity, example))

        # Sort by similarity (highest first) and return top_k
        similarities.sort(reverse=True, key=lambda x: x[0])

        top_examples = [example for _, example in similarities[:top_k]]

        # Log retrieval for monitoring
        if top_examples:
            logger.info(
                "few_shot_examples_retrieved",
                query=query[:100],
                count=len(top_examples),
                categories=[e.category for e in top_examples],
                similarities=[f"{sim:.3f}" for sim, _ in similarities[:top_k]],
            )
        else:
            logger.warning(
                "no_similar_examples_found",
                query=query[:100],
                min_similarity=min_similarity,
            )

        return top_examples

    def get_examples_by_category(self, category: str) -> List[SQLExample]:
        """Get all examples in a specific category"""
        return [e for e in self.examples if e.category == category]

    def get_all_categories(self) -> List[str]:
        """Get list of all unique categories"""
        return list(set(e.category for e in self.examples))

    def format_examples_for_prompt(self, examples: List[SQLExample]) -> str:
        """
        Format examples for inclusion in LLM prompt.

        Args:
            examples: List of SQLExample objects to format

        Returns:
            Formatted string ready for prompt injection
        """
        if not examples:
            return ""

        prompt = "\n═══════════════════════════════════════════════════════════════\n"
        prompt += "📚 SIMILAR EXAMPLE QUERIES (Learn from these)\n"
        prompt += "═══════════════════════════════════════════════════════════════\n\n"

        for i, example in enumerate(examples, 1):
            prompt += f"EXAMPLE {i}:\n"
            prompt += f"Question: {example.question}\n\n"
            prompt += f"SQL:\n{example.sql}\n"
            if example.notes:
                prompt += f"\n💡 Note: {example.notes}\n"
            prompt += "\n" + "-" * 60 + "\n\n"

        return prompt

    def add_example(
        self,
        category: str,
        question: str,
        sql: str,
        notes: Optional[str] = None,
        difficulty: str = "medium",
    ):
        """
        Add a new example dynamically (useful for continuous learning).

        Args:
            category: Example category
            question: Natural language question
            sql: SQL query
            notes: Optional notes about the example
            difficulty: Difficulty level (easy, medium, hard)
        """
        example = SQLExample(
            category=category,
            question=question,
            sql=sql,
            notes=notes,
            difficulty=difficulty,
        )

        # Compute embedding using singleton model
        example.embedding = np.array(self.embedding_model.encode_single(question))

        self.examples.append(example)

        logger.info(
            "few_shot_example_added",
            category=category,
            question=question[:100],
            total_examples=len(self.examples),
        )

    def get_stats(self) -> Dict:
        """Get statistics about the example store"""
        return {
            "total_examples": len(self.examples),
            "categories": self.get_all_categories(),
            "examples_per_category": {
                cat: len(self.get_examples_by_category(cat))
                for cat in self.get_all_categories()
            },
            "difficulty_distribution": {
                "easy": len([e for e in self.examples if e.difficulty == "easy"]),
                "medium": len([e for e in self.examples if e.difficulty == "medium"]),
                "hard": len([e for e in self.examples if e.difficulty == "hard"]),
            },
        }


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_few_shot_store_instance = None


def get_few_shot_store() -> FewShotSQLStore:
    """
    Get or create the singleton FewShotSQLStore instance.
    Uses lazy initialization to avoid loading on import.
    """
    global _few_shot_store_instance
    if _few_shot_store_instance is None:
        logger.info("few_shot_store_singleton_initializing")
        _few_shot_store_instance = FewShotSQLStore()
        logger.info("few_shot_store_singleton_ready")
    return _few_shot_store_instance


def reset_few_shot_store():
    """
    Reset the singleton instance (useful for testing).
    WARNING: Only use this for testing purposes.
    """
    global _few_shot_store_instance
    _few_shot_store_instance = None
    logger.warning("few_shot_store_singleton_reset")
