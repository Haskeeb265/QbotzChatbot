from typing import Dict, Any, Optional, List
import re
from groq import Groq
from core.agents.base_agent import BaseAgent
from core.storage.sap_sync.db_queries import DataAccess, DatabaseConnection
from config.settings import settings

# Load SQL reference patterns for few-shot learning
try:
    from sql_reference.query_patterns import get_few_shot_examples_text

    SQL_REFERENCE_AVAILABLE = True
except ImportError:
    SQL_REFERENCE_AVAILABLE = False


class SQLAgent(BaseAgent):
    """
    SQLAgent with dynamic schema retrieval and smart column prioritization.
    No hardcoded columns - adapts to any database schema automatically.
    """

    def __init__(self):
        super().__init__("sql_agent")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
        self.db = DataAccess()

        # Dynamically fetch and cache schema
        self.schema = self._fetch_dynamic_schema()
        self.important_columns = self._identify_important_columns()

        # Load SQL reference patterns (few-shot examples)
        if SQL_REFERENCE_AVAILABLE:
            try:
                self.few_shot_examples = get_few_shot_examples_text(max_examples=5)
                self.logger.info("sql_reference_patterns_loaded", status="success")
            except Exception as e:
                self.few_shot_examples = ""
                self.logger.warning(
                    "sql_reference_load_failed", error=str(e), fallback="no_examples"
                )
        else:
            self.few_shot_examples = ""
            self.logger.info("sql_reference_not_available")

        self.logger.info(
            "sql_agent_initialized",
            total_columns=len(self.schema),
            important_columns=len(self.important_columns),
            has_reference_patterns=bool(self.few_shot_examples),
        )

    # ================================================================
    # DYNAMIC SCHEMA FETCHING
    # ================================================================

    def _fetch_dynamic_schema(self) -> Dict[str, str]:
        """
        Fetch complete schema information from PostgreSQL's information_schema.
        Returns: Dict mapping column_name -> formatted_type
        """
        query = """
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'sales_orders'
        ORDER BY ordinal_position;
        """

        try:
            conn = DatabaseConnection.get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = cur.fetchall()

                    schema = {}
                    for col in columns:
                        col_name = col[0]
                        data_type = col[1]
                        char_max = col[2]
                        num_precision = col[3]
                        num_scale = col[4]

                        # Format type with precision/length info
                        formatted_type = self._format_column_type(
                            data_type, char_max, num_precision, num_scale
                        )

                        schema[col_name] = formatted_type

                    self.logger.info(
                        "schema_fetched_successfully",
                        column_count=len(schema),
                        table="sales_orders",
                    )
                    return schema

            finally:
                DatabaseConnection.return_connection(conn)

        except Exception as e:
            self.logger.error(
                "schema_fetch_failed",
                error_type=type(e).__name__,
                error=str(e),
                fallback="empty_schema",
            )
            # Return empty dict as fallback
            return {}

    def _format_column_type(
        self,
        data_type: str,
        char_max_len: Optional[int],
        numeric_precision: Optional[int],
        numeric_scale: Optional[int],
    ) -> str:
        """
        Convert PostgreSQL data types to readable format.
        Examples:
          - character varying(50) -> VARCHAR(50)
          - numeric(10,2) -> DECIMAL(10,2)
          - timestamp without time zone -> TIMESTAMP
        """
        # Map PostgreSQL types to common names
        type_map = {
            "character varying": "VARCHAR",
            "character": "CHAR",
            "timestamp without time zone": "TIMESTAMP",
            "timestamp with time zone": "TIMESTAMPTZ",
            "double precision": "DOUBLE",
            "bigint": "BIGINT",
            "integer": "INTEGER",
            "smallint": "SMALLINT",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "jsonb": "JSONB",
            "text": "TEXT",
            "numeric": "DECIMAL",
            "real": "REAL",
            "USER-DEFINED": "CUSTOM",
        }

        base_type = type_map.get(data_type.lower(), data_type.upper())

        # Add precision/length information
        if char_max_len:
            return f"{base_type}({char_max_len})"
        elif numeric_precision and numeric_scale is not None:
            return f"{base_type}({numeric_precision},{numeric_scale})"
        elif numeric_precision:
            return f"{base_type}({numeric_precision})"

        return base_type

    # ================================================================
    # SMART COLUMN PRIORITIZATION
    # ================================================================

    def _identify_important_columns(self) -> Dict[str, str]:
        """
        Automatically identify analytically important columns based on:
        - Business keywords (revenue, customer, date, etc.)
        - Common analytical patterns
        - Naming conventions

        Returns: Dict of {column_name: "TYPE - Description"}
        """
        # Keywords that indicate analytical importance
        priority_keywords = {
            # Identifiers
            "id",
            "key",
            "number",
            "code",
            "party",
            # Financial
            "amount",
            "revenue",
            "price",
            "cost",
            "value",
            "total",
            "net",
            # Temporal
            "date",
            "time",
            "created",
            "updated",
            "modified",
            # Organizational
            "organization",
            "division",
            "department",
            "group",
            "office",
            "district",
            # Customer/Sales
            "customer",
            "sold",
            "ship",
            "sales",
            "order",
            "purchase",
            # Status/State
            "status",
            "state",
            "condition",
            "block",
            "approval",
            # References
            "reference",
            "document",
            "type",
            "category",
            # Location
            "region",
            "territory",
            "location",
            "country",
        }

        important = {}

        for col_name, col_type in self.schema.items():
            lower_name = col_name.lower()

            # Check if column matches any important keyword
            if any(keyword in lower_name for keyword in priority_keywords):
                # Generate semantic description
                description = self._generate_column_description(col_name, col_type)
                important[col_name] = f"{col_type} - {description}"

        self.logger.info(
            "important_columns_identified",
            total=len(self.schema),
            important=len(important),
            percentage=f"{(len(important)/max(len(self.schema), 1)*100):.1f}%",
        )

        return important

    def _generate_column_description(self, col_name: str, col_type: str) -> str:
        """
        Auto-generate semantic descriptions based on column name patterns.
        Makes schema more understandable for LLM.
        """
        lower_name = col_name.lower()

        # Financial columns
        if "total_net_amount" in lower_name:
            return "Primary Revenue/Sales Amount"
        if "amount" in lower_name or "value" in lower_name:
            return "Financial Value"
        if "price" in lower_name:
            return "Pricing Information"
        if "cost" in lower_name:
            return "Cost Data"

        # Customer/Party columns
        if "sold_to_party" in lower_name:
            return "Primary Customer ID"
        if "ship_to_party" in lower_name:
            return "Shipping Customer ID"
        if "customer" in lower_name:
            return "Customer Information"
        if "party" in lower_name:
            return "Business Partner"

        # Date columns
        if "sales_order_date" in lower_name:
            return "Primary Transaction Date"
        if "creation_date" in lower_name or "created" in lower_name:
            return "Record Creation Date"
        if "delivery_date" in lower_name:
            return "Delivery/Shipping Date"
        if "billing_date" in lower_name:
            return "Invoice Date"
        if "date" in lower_name:
            return "Date Field"

        # Identifiers
        if "sales_order" in lower_name and (
            "id" in lower_name or "number" in lower_name or col_name == "sales_order"
        ):
            return "Primary Order Identifier"
        if col_name.endswith("_id") or "number" in lower_name or "code" in lower_name:
            return "Identifier/Code"

        # Status fields
        if "status" in lower_name:
            return "Process Status"
        if "block" in lower_name:
            return "Blocking/Hold Status"
        if "approval" in lower_name:
            return "Approval Status"

        # Organizational
        if "organization" in lower_name:
            return "Organizational Unit"
        if "division" in lower_name:
            return "Business Division"
        if "office" in lower_name or "group" in lower_name:
            return "Sales Unit"

        # References
        if "reference" in lower_name:
            return "External Reference"
        if "document" in lower_name:
            return "Document Reference"

        # Type/Category
        if "type" in lower_name:
            return "Type/Category"
        if "category" in lower_name:
            return "Classification"

        # Default
        return "Analytical Field"

    # ================================================================
    # SCHEMA FORMATTING FOR LLM
    # ================================================================

    def _format_schema(self) -> str:
        """
        Format schema for LLM consumption.
        Shows important columns first, then mentions others exist.
        """
        lines = ["=== KEY ANALYTICAL COLUMNS ==="]

        # Show important columns with descriptions
        for col_name, full_desc in sorted(self.important_columns.items()):
            lines.append(f"  • {col_name}: {full_desc}")

        # Mention additional columns
        other_count = len(self.schema) - len(self.important_columns)
        if other_count > 0:
            lines.append(f"\n=== ADDITIONAL COLUMNS ===")
            lines.append(
                f"  ... plus {other_count} more columns available in sales_orders table"
            )
            lines.append(
                f"  (You can reference any column; these are just the most commonly used)"
            )

        return "\n".join(lines)

    def _format_full_schema(self) -> str:
        """
        Return complete schema (useful for debugging/detailed analysis).
        """
        lines = ["=== COMPLETE SCHEMA: sales_orders ==="]
        for col_name, col_type in sorted(self.schema.items()):
            lines.append(f"  {col_name}: {col_type}")
        return "\n".join(lines)

    # ================================================================
    # MAIN EXECUTION
    # ================================================================

    def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for SQL generation.
        Returns standardized response with 'success' and 'result' keys.
        """
        try:
            self.logger.info("generating_sql", query=query)

            sql = self._generate_sql(query, context)

            # Policy validation (no dangerous keywords)
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

            # Syntax validation (EXPLAIN test)
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

            # Success
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

    # ================================================================
    # SQL GENERATION
    # ================================================================

    def _generate_sql(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate SQL using LLM with dynamic schema and conversation context.
        """
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
If the current question is a follow-up, resolve vague references (e.g., "those regions", "the same period", "compare again") using the previous question:
"{last_query}"
"""

        # Include few-shot examples if available
        examples_section = ""
        if self.few_shot_examples:
            examples_section = f"""
{self.few_shot_examples}

IMPORTANT: Use these examples as REFERENCE PATTERNS to understand:
- How to structure queries (CTEs, subqueries, aggregations)
- Common analytical patterns (time series, comparisons, rankings)
- Best practices (NULLIF for division, explicit date ranges, proper grouping)

DO NOT copy these queries directly - adapt the patterns to answer the specific question.
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

{examples_section}

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

TIME PERIOD RULES:
- For "historical vs current" comparisons, use EQUAL time windows
- Default: Compare last 12 months vs previous 12 months
- For "declining" questions, calculate month-over-month or year-over-year rates
- Example: 
  Historical = 2024-01-01 to 2024-12-31
  Current = 2025-01-01 to 2025-12-31

RATE NORMALIZATION:
- When comparing time periods, divide by period length to get rates
- Compare revenue/month or revenue/day, not total revenue
- This prevents bias from unequal time windows

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
            temperature=0,  # Deterministic output - same prompt always gives same SQL
            max_tokens=1500,  # Prevent truncation of complex queries
        )

        sql = response.choices[0].message.content.strip()
        # Remove markdown code fences if present
        sql = sql.replace("```sql", "").replace("```", "").strip()

        return sql

    # ================================================================
    # VALIDATION
    # ================================================================

    def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Policy validation - checks for dangerous keywords.
        Does NOT validate syntax (that's done in _dry_run_validate).
        """
        sql_clean = sql.strip()
        sql_upper = sql_clean.upper()

        # Must start with SELECT or WITH
        if not re.match(r"^(SELECT|WITH\s+.+?\s+SELECT)\b", sql_upper, re.DOTALL):
            self.logger.warning(
                "sql_validation_failed",
                reason="not_select_statement",
                sql=sql[:200],
            )
            return {"valid": False, "reason": "not_select_statement"}

        # Check for forbidden keywords
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
                self.logger.warning(
                    "sql_validation_failed",
                    reason="forbidden_keyword",
                    keyword=keyword,
                    sql=sql[:200],
                )
                return {
                    "valid": False,
                    "reason": f"forbidden_keyword:{keyword}",
                }

        return {"valid": True, "reason": None}

    def _dry_run_validate(self, sql: str) -> bool:
        """
        Syntax validation using PostgreSQL's EXPLAIN.
        Returns True if SQL is syntactically correct.
        """
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

    # ================================================================
    # ERROR HANDLING
    # ================================================================

    def _handle_error(self, e: Exception, query: str) -> Dict[str, Any]:
        """
        Standardized error handler.
        Always returns proper response structure with empty result list.
        """
        self.logger.error(
            "sql_agent_error",
            error_type=type(e).__name__,
            error=str(e),
            query=query[:200],
        )

        return self._create_response(
            success=False,
            error=f"Internal error: {type(e).__name__}",
            result=[],  # ✅ Always return empty list on error
        )

    # ================================================================
    # UTILITY METHODS
    # ================================================================

    def get_schema_summary(self) -> Dict[str, Any]:
        """Public method to inspect current schema (useful for debugging)"""
        return {
            "total_columns": len(self.schema),
            "important_columns": len(self.important_columns),
            "all_columns": list(self.schema.keys()),
            "important_column_names": list(self.important_columns.keys()),
        }

    def refresh_schema(self) -> None:
        """Manually refresh schema (useful after database changes)"""
        self.logger.info("refreshing_schema")
        self.schema = self._fetch_dynamic_schema()
        self.important_columns = self._identify_important_columns()
        self.logger.info(
            "schema_refreshed",
            total_columns=len(self.schema),
            important_columns=len(self.important_columns),
        )
