from typing import Dict, Any, List
from core.storage.embedding.embedding_manager import EmbeddingModelManager
from core.storage.embedding.text_formatter import SalesOrderFormatter
from core.storage.sap_sync.db_queries import DatabaseConnection
from utility.observability.logger import get_logger

logger = get_logger("embedding_service")


class EmbeddingService:

    def __init__(self):
        self.model = EmbeddingModelManager.get_instance()
        self.formatter = SalesOrderFormatter()

    def embed_all_sales_orders(self) -> Dict[str, int]:

        logger.info("embedding_all_starting")

        conn = DatabaseConnection.get_connection()

        try:
            with conn.cursor() as cur:
                # Fetch records without embeddings
                records = self._fetch_unembed_records(cur)

                if not records:
                    logger.info("no_records_to_embed")
                    return {"embedded": 0, "skipped": 0, "errors": 0}

                # Convert to text
                texts = self._prepare_texts(records)

                # Generate embeddings
                embeddings = self._generate_embeddings(texts)

                # Update database
                stats = self._update_database(cur, records, embeddings)

                conn.commit()
                logger.info("embedding_complete", **stats)

                return stats

        except Exception as e:
            conn.rollback()
            logger.error("embedding_batch_failed", error=e)
            raise
        finally:
            DatabaseConnection.return_connection(conn)

    def _fetch_unembed_records(self, cursor) -> List[Dict[str, Any]]:
        cursor.execute(
            """
            SELECT 
                sales_order, sold_to_party, total_net_amount,
                transaction_currency, sales_district, sales_office,
                overall_delivery_status, sales_order_date, sales_order_type
            FROM sales_orders
            WHERE embedding IS NULL
            ORDER BY sales_order;
        """
        )

        records = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        records_dicts = [dict(zip(columns, row)) for row in records]

        logger.info("records_fetched", count=len(records_dicts))
        return records_dicts

    def _prepare_texts(self, records: List[Dict[str, Any]]) -> List[str]:
        """Convert records to searchable text"""
        texts = []

        for record in records:
            if self.formatter.validate_record(record):
                text = self.formatter.to_searchable_text(record)
                texts.append(text)
            else:
                texts.append("")  # Invalid record, use empty string

        logger.info("texts_prepared", count=len(texts))
        return texts

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batches"""
        logger.info("generating_embeddings", count=len(texts))
        return self.model.encode_batch(texts)

    def _update_database(
        self, cursor, records: List[Dict[str, Any]], embeddings: List[List[float]]
    ) -> Dict[str, int]:
        """Update database with embeddings"""
        logger.info("updating_database", count=len(embeddings))

        embedded_count = 0
        errors = 0

        for record, embedding in zip(records, embeddings):
            try:
                cursor.execute(
                    """
                    UPDATE sales_orders 
                    SET embedding = %s 
                    WHERE sales_order = %s
                """,
                    (embedding, record["sales_order"]),
                )

                embedded_count += 1

                # Progress logging
                if embedded_count % 1000 == 0:
                    logger.info(
                        "embedding_progress",
                        processed=embedded_count,
                        total=len(embeddings),
                    )

            except Exception as e:
                errors += 1
                logger.error(
                    "embedding_update_failed",
                    sales_order=record["sales_order"],
                    error=str(e),
                )

        return {"embedded": embedded_count, "skipped": 0, "errors": errors}
