from typing import Dict, Any, Optional, List
from datetime import datetime
from utility.services.sap_client import SAPClient
from core.storage.sap_sync.transformers import SAPTransformer
from core.storage.sap_sync.upsert_operations import UpsertOperations
from core.storage.sap_sync.db_queries import DatabaseConnection
from utility.observability.logger import get_logger

logger = get_logger("sap_sync")


class SAPSyncService:
    """
    Orchestrates SAP → PostgreSQL sync

    WHY THIS DESIGN?
    - Single Responsibility: Only coordinates, doesn't transform or upsert
    - Clean: Easy to read and understand flow
    - Testable: Can mock SAPClient, transformer, upserter
    """

    def __init__(self):
        self.sap_client = SAPClient()
        self.transformer = SAPTransformer()
        self.upserter = UpsertOperations()

    def sync_sales_orders(self, filters: Optional[str] = None) -> Dict[str, Any]:
        """
        Main sync: SAP → Transform → PostgreSQL

        Returns:
            {"inserted": 100, "updated": 50, "unchanged": 900, "errors": 0, "duration_seconds": 12.3}
        """
        sync_start = datetime.utcnow()
        logger.info("sync_starting", filters=filters)

        # Step 1: Fetch from SAP
        sap_records = self._fetch_sap_data(filters)

        # Step 2: Transform & Upsert
        stats = self._process_records(sap_records)

        # Step 3: Add duration
        stats["duration_seconds"] = round(
            (datetime.utcnow() - sync_start).total_seconds(), 2
        )

        logger.info("sync_completed", **stats)
        return stats

    def _fetch_sap_data(self, filters: Optional[str]) -> List[Dict[str, Any]]:
        """Fetch records from SAP with error handling"""
        try:
            records = self.sap_client.fetch_all_sales_orders(filters)
            logger.info("sap_fetch_completed", record_count=len(records))
            return records
        except Exception as e:
            logger.error("sap_fetch_failed", error=e)
            raise

    def _process_records(self, sap_records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Transform and upsert all records"""
        stats = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0}

        conn = DatabaseConnection.get_connection()

        try:
            with conn.cursor() as cur:
                for idx, sap_record in enumerate(sap_records, 1):
                    try:
                        # Transform
                        pg_record = self.transformer.transform_sales_order(sap_record)

                        # Upsert
                        result = self.upserter.upsert_record(cur, pg_record)
                        stats[result] += 1

                        # Progress every 1000 records
                        if idx % 1000 == 0:
                            logger.info(
                                "sync_progress",
                                processed=idx,
                                total=len(sap_records),
                                percent=round(idx / len(sap_records) * 100, 1),
                            )

                    except Exception as e:
                        stats["errors"] += 1
                        logger.error(
                            "record_processing_failed",
                            sales_order=sap_record.get("SalesOrder"),
                            error=str(e),
                        )

                conn.commit()
                logger.info("batch_committed", **stats)

        except Exception as e:
            conn.rollback()
            logger.error("batch_failed", error=e)
            raise
        finally:
            DatabaseConnection.return_connection(conn)

        return stats
