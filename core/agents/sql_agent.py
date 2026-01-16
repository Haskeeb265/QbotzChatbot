from typing import Dict, Any, Optional
import re

from groq import Groq

from core.agents.base_agent import BaseAgent
from core.storage.sap_sync.db_queries import DataAccess, DatabaseConnection
from config.settings import settings


class SQLAgent(BaseAgent):
    def __init__(self):
        super().__init__("sql_agent")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
        self.db = DataAccess()
        self.schema = self.db.get_sales_schema()

    # ------------------------------------------------------------------
    # ENTRY POINT
    # ------------------------------------------------------------------

    def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            self.logger.info("generating_sql", query=query)

            sql = self._generate_sql(query, context)

            validation = self._validate_sql(sql)
            if not validation["valid"]:
                return self._create_response(
                    success=False,
                    result={
                        "sql": sql,
                        "sql_generated": True,
                        "sql_validated": False,
                        "sql_reject_reason": validation["reason"],
                    },
                    error="Generated SQL failed policy validation",
                )

            if not self._dry_run_validate(sql):
                return self._create_response(
                    success=False,
                    result={
                        "sql": sql,
                        "sql_generated": True,
                        "sql_validated": True,
                        "sql_syntax_ok": False,
                    },
                    error="Generated SQL has syntax errors",
                )

            return self._create_response(
                success=True,
                result={
                    "sql": sql,
                    "sql_generated": True,
                    "sql_validated": True,
                    "sql_syntax_ok": True,
                },
            )

        except Exception as e:
            return self._handle_error(e, query)

    # ------------------------------------------------------------------
    # SQL GENERATION
    # ------------------------------------------------------------------

    def _generate_sql(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        from core.graphs.conversation_utils import (
            format_conversation_context,
            get_last_query_context,
        )

        conversation_context = ""
        last_query = None

        if context and context.get("conversation_history"):
            conversation_context = format_conversation_context(
                context.get("conversation_history"),
                max_turns=2,
            )
            last_query = get_last_query_context(context.get("conversation_history"))

        if conversation_context:
            conversation_context = f"""
{conversation_context}

FOLLOW-UP RESOLUTION RULE:
If the current question is a follow-up, resolve vague references
(e.g., "those regions", "the same period", "compare again")
using the previous question:
"{last_query}"
"""

        prompt = f"""
You are an expert PostgreSQL query generator for SAP sales analytics.
You think like a data analyst, not a keyword matcher.

{conversation_context}

QUESTION:
{query}

DATABASE:
Table: sales_orders

SCHEMA:
{self._format_schema()}

ANALYTICAL INTENT RULES (MANDATORY):
- If the question mentions decline, growth, increase, decrease, trend, change, or performance over time:
  - You MUST compare the same entity across at least two time periods
  - Ranking, NOT IN, or exclusion logic is NOT a valid substitute
  - Use time-based aggregation and explicit comparison

- If the question mentions historical vs current:
  - Clearly define two time ranges
  - Compute metrics per range
  - Compare them explicitly in the outer query

- If a comparison cannot be made due to insufficient data:
  - Return all computed results rather than forcing a conclusion

FORBIDDEN HEURISTICS:
- NEVER use ranking exclusion (NOT IN with ORDER BY + LIMIT) to imply decline or growth
- NEVER infer trends from rank position alone
- NEVER answer analytical questions using absence of data as evidence

ABSOLUTE SQL RULES:
1. Single-table queries only.
2. Use only schema columns.
3. Use total_net_amount for revenue.
4. Use sold_to_party for customer identity.
5. Use sales_order_date for date filters.
6. Always include LIMIT <= 1000 unless computing aggregates for highest/lowest logic.
7. NEVER use SELECT *.
8. When filtering strings, always use UPPER(column) = UPPER(value).
9. Output SQL only — no comments, no markdown.

HIGHEST / LOWEST RULES:
10. For highest or lowest questions:
    - Return ALL entities tied for highest or lowest
    - DO NOT use LIMIT 1
    - Use MAX() or MIN() via subquery or CTE

WINDOW FUNCTION RULES:
11. Window functions (LAG, LEAD, etc.) are allowed ONLY inside subqueries or CTEs.
12. NEVER use window functions directly in WHERE or HAVING.
13. Perform filtering only in the outer query.

SANITY CHECK BEFORE FINALIZING:
- Does the SQL directly answer the question asked?
- Does it rely on explicit computation rather than inference?
- Would a human analyst accept this logic?

SQL:
"""

        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        sql = response.choices[0].message.content.strip()
        return sql.replace("```sql", "").replace("```", "").strip()

    # ------------------------------------------------------------------
    # POLICY VALIDATION (NOT SYNTAX)
    # ------------------------------------------------------------------

    def _validate_sql(self, sql: str) -> Dict[str, Any]:
        sql_clean = sql.strip()
        sql_upper = sql_clean.upper()

        if not re.match(r"^(SELECT|WITH\s+.+?\s+SELECT)\b", sql_upper, re.DOTALL):
            return {"valid": False, "reason": "not_select_statement"}

        forbidden = {
            "DROP",
            "DELETE",
            "UPDATE",
            "INSERT",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "GRANT",
        }

        for keyword in forbidden:
            if re.search(rf"\b{keyword}\b", sql_upper):
                return {"valid": False, "reason": f"forbidden_keyword:{keyword}"}

        return {"valid": True, "reason": None}

    # ------------------------------------------------------------------
    # DRY-RUN SYNTAX CHECK
    # ------------------------------------------------------------------

    def _dry_run_validate(self, sql: str) -> bool:
        try:
            test_query = f"EXPLAIN {sql}"
            conn = DatabaseConnection.get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(test_query)
                    return True
            finally:
                DatabaseConnection.return_connection(conn)
        except Exception as e:
            self.logger.warning(
                "sql_dry_run_failed",
                error_type=type(e).__name__,
                error_message=str(e)[:200],
                sql=sql[:200],
            )
            return False

    # ------------------------------------------------------------------
    # SCHEMA FORMATTING
    # ------------------------------------------------------------------

    def _format_schema(self) -> str:
        lines = ["Key columns:"]
        for col, dtype in self.schema.items():
            lines.append(f"  • {col}: {dtype}")
        return "\n".join(lines)
