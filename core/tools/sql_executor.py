from typing import Any, Dict, List

from core.storage.sap_sync.db_queries import DataAccess
from utility.observability.logger import get_logger

logger = get_logger("sql_executor")


def execute_sql(sql: str) -> List[Dict[str, Any]]:
    """Execute SQL and return results"""
    db = DataAccess()

    logger.info("sql_execution_started", sql=sql[:100])

    try:
        results = db.execute_sql(sql)
        logger.info("sql_executed", rows=len(results))
        return results
    except Exception as e:
        logger.error("sql_execution_failed", error=str(e))
        raise
