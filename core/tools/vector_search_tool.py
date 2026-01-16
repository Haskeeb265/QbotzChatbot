from typing import List, Dict, Any
from core.storage.embedding import EmbeddingModelManager
from core.storage.sap_sync.db_queries import DatabaseConnection
from utility.observability.logger import get_logger

logger = get_logger("vector_search_tool")


def vector_search(
    query: str, limit: int = 10, similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Perform vector similarity search (TOOL function).

    Args:
        query (str): Search query (can be expanded)
        limit (int): Maximum number of results
        similarity_threshold (float): Minimum similarity score to include

    Returns:
        List[Dict[str, Any]]: Matching sales orders with similarity scores
    """
    # Generate query embedding using singleton (eliminates 7s delay)
    model = EmbeddingModelManager.get_instance()
    query_embedding = model.encode_single(query)

    conn = DatabaseConnection.get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    sales_order,
                    sold_to_party,
                    total_net_amount,
                    transaction_currency,
                    sales_district,
                    overall_delivery_status,
                    sales_order_date,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM sales_orders
                WHERE embedding IS NOT NULL
                  AND 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (query_embedding, query_embedding, similarity_threshold, query_embedding, limit),
            )

            results = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            results_dicts = [dict(zip(columns, row)) for row in results]

            logger.info(
                "vector_search_completed",
                query=query[:100],
                results_count=len(results_dicts),
            )

            return results_dicts

    finally:
        DatabaseConnection.return_connection(conn)
