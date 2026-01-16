from typing import Dict, Any
from core.tools import execute_sql
from utility.observability.logger import get_logger

logger = get_logger("sql_flow")


class SQLExecutionFlow:
    """
    Handles SQL generation + execution as a single responsibility unit.
    """

    def __init__(self, sql_agent):
        self.sql_agent = sql_agent

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("sql_flow_start", query=state["query"])

        context = {
            "conversation_history": state.get("conversation_history", []),
            "conversation_resolution": state.get("conversation_resolution"),
        }

        result = self.sql_agent.run(state["query"], context)

        if not result["success"]:
            state["error"] = result["error"]
            return state

        sql = result["result"]["sql"]
        state["sql"] = sql

        try:
            state["sql_results"] = execute_sql(sql)
        except Exception as e:
            logger.error("sql_execution_failed", error=str(e))
            state["error"] = str(e)

        return state
