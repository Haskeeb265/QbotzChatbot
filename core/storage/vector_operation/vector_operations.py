from typing import List, Dict, Any

from utility.observability.logger import get_logger
from core.storage.embedding.embedding_model import EmbeddingModel
from core.storage.sap_sync.db_queries import DatabaseConnection

logger = get_logger("vector_operations")


class VectorSearch:

    def __init__(self) -> None:
        self.model = EmbeddingModel()

    def search(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:

        # Generate query embedding
        query_embedding = self.model.encode_single(query)

        conn = DatabaseConnection.get_connection()

        try:
            with conn.cursor() as cur:
                # PgVector cosine similarity search
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
                    (
                        query_embedding,
                        query_embedding,
                        similarity_threshold,
                        query_embedding,
                        limit,
                    ),
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
