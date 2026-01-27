import re
from typing import Any, Dict, List, Optional

from groq import Groq

from config.settings import settings
from core.agents.base_agent import BaseAgent
from core.storage.sap_sync.db_queries import DataAccess, DatabaseConnection


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

        self.logger.info(
            "sql_agent_initialized",
            total_columns=len(self.schema),
            important_columns=len(self.important_columns),
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
            percentage=f"{(len(important) / len(self.schema) * 100):.1f}%",
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
        Generate SQL using LLM with schema and conversation context.
        """
        from core.graphs.conversation_utils import format_conversation_context

        conversation_context = ""
        if context and context.get("conversation_history"):
            conversation_context = format_conversation_context(
                context["conversation_history"],
                max_turns=2,
            )

        prompt = f"""You are a PostgreSQL query generator.

   DATABASE SCHEMA:
   {self._format_schema()}

   USER QUESTION:
   {query}

   RULES:
   1. Return ONLY the SQL query
   2. NO explanations, descriptions, or comments
   3. NO markdown formatting or code blocks
   4. Start directly with SELECT or WITH
   5. Query must be read-only (SELECT/WITH only)
   6. Use the sales_orders table

   IMPORTANT POSTGRESQL SYNTAX RULES:
   - When using UNION with ORDER BY and LIMIT, wrap each query in parentheses
   - Example: (SELECT ... ORDER BY ... LIMIT 1) UNION ALL (SELECT ... ORDER BY ... LIMIT 1)
   - For CTEs (WITH clause), use proper syntax: WITH cte AS (...) SELECT ...
   - Always use explicit type casting when needed: ::integer, ::date, etc.

   EXAMPLES:
   Question: How many orders?
   SELECT COUNT(*) FROM sales_orders;

   Question: Top 5 customers by revenue?
   SELECT customer_name, SUM(total_net_amount) as revenue
   FROM sales_orders
   GROUP BY customer_name
   ORDER BY revenue DESC
   LIMIT 5;

   Question: Highest and lowest revenue regions?
   (SELECT sales_district, SUM(total_net_amount) as revenue
    FROM sales_orders
    GROUP BY sales_district
    ORDER BY revenue DESC
    LIMIT 1)
   UNION ALL
   (SELECT sales_district, SUM(total_net_amount) as revenue
    FROM sales_orders
    GROUP BY sales_district
    ORDER BY revenue ASC
    LIMIT 1);

   Now generate ONLY the SQL query for the user's question (no explanations):
   """

        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )

        sql = response.choices[0].message.content.strip()

        # Clean up any potential markdown or extra text
        sql = sql.replace("```sql", "").replace("```", "").strip()

        # If LLM still adds explanatory text, try to extract just the SQL
        if not sql.upper().startswith(
            ("SELECT", "WITH", "(")
        ):  # ← Added "(" for wrapped queries
            # Look for SELECT or WITH statement in the response
            lines = sql.split("\n")
            for line in lines:
                line = line.strip()
                if line.upper().startswith(("SELECT", "WITH", "(")):
                    sql = line
                    break

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

        # ================================================================
        # 1️⃣ Must start with SELECT or WITH (allow leading parentheses/whitespace)
        # ================================================================
        if not re.match(r"^\s*(\(+\s*)*(SELECT|WITH)\b", sql_upper, re.DOTALL):
            self.logger.warning(
                "sql_validation_failed",
                reason="not_select_statement",
                sql=sql[:200],
            )
            return {"valid": False, "reason": "not_select_statement"}

        # ================================================================
        # 2️⃣ Forbidden keywords check
        # ================================================================
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
                return {"valid": False, "reason": f"forbidden_keyword:{keyword}"}

        # ================================================================
        # ✅ Passed all checks
        # ================================================================
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
