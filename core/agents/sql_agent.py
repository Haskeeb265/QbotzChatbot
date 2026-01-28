import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Set, Tuple

from groq import Groq

from config.settings import settings
from core.agents.base_agent import BaseAgent
from core.storage.sap_sync.db_queries import DataAccess, DatabaseConnection
from core.tools.get_few_shot_store import get_few_shot_store


class SQLAgent(BaseAgent):
    def __init__(self):
        super().__init__("sql_agent")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
        self.db = DataAccess()

        # Dynamically fetch and cache schema
        self.schema = self._fetch_dynamic_schema()
        self.important_columns = self._identify_important_columns()
        self.few_shot_store = get_few_shot_store()

        self.logger.info(
            "sql_agent_initialized",
            total_columns=len(self.schema),
            important_columns=len(self.important_columns),
            few_shot_examples=self.few_shot_store.get_stats()["total_examples"],
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
    # LAYER 1: ENHANCED SCHEMA PROMPT (ANTI-HALLUCINATION)
    # ================================================================

    def _get_categorized_columns(self) -> Dict[str, List[str]]:
        """
        Organize columns by business domain for clearer LLM understanding.
        Returns dict of category -> list of exact column names.
        """

        # Get all column names from schema
        all_columns = set(self.schema.keys())

        # All columns organized by purpose
        categories = {
            "🎯 Primary Identifiers": [
                col
                for col in ["sales_order", "sold_to_party", "external_document_id"]
                if col in all_columns
            ],
            "📅 Dates & Timestamps": [
                col
                for col in [
                    "sales_order_date",
                    "creation_date",
                    "billing_document_date",
                    "customer_purchase_order_date",
                    "requested_delivery_date",
                    "services_rendered_date",
                    "pricing_date",
                    "last_change_date",
                    "last_change_date_time",
                    "external_doc_last_change_date_time",
                    "first_synced_at",
                    "last_updated_at",
                ]
                if col in all_columns
            ],
            "💰 Financial & Amounts": [
                col
                for col in [
                    "total_net_amount",
                    "transaction_currency",
                    "accounting_exchange_rate",
                    "price_detn_exchange_rate",
                ]
                if col in all_columns
            ],
            "🏢 Organizational Structure": [
                col
                for col in [
                    "sales_organization",
                    "distribution_channel",
                    "organization_division",
                    "sales_district",
                    "sales_office",
                    "sales_group",
                ]
                if col in all_columns
            ],
            "👥 Customer Classification": [
                col
                for col in [
                    "customer_group",
                    "customer_price_group",
                    "customer_account_assignment_group",
                    "customer_condition_group1",
                    "customer_condition_group2",
                    "customer_condition_group3",
                    "customer_condition_group4",
                    "customer_condition_group5",
                    "additional_customer_group1",
                    "additional_customer_group2",
                    "additional_customer_group3",
                    "additional_customer_group4",
                    "additional_customer_group5",
                ]
                if col in all_columns
            ],
            "📦 Delivery & Shipping": [
                col
                for col in [
                    "overall_delivery_status",
                    "overall_total_delivery_status",
                    "shipping_condition",
                    "shipping_type",
                    "delivery_block_reason",
                    "delivery_date_type_rule",
                    "complete_delivery_is_defined",
                    "sls_doc_is_rlvt_for_proof_of_deliv",
                ]
                if col in all_columns
            ],
            "💳 Billing & Payment": [
                col
                for col in [
                    "overall_ord_reltd_billg_status",
                    "header_billing_block_reason",
                    "billing_plan",
                    "customer_payment_terms",
                    "payment_method",
                    "fixed_value_date",
                    "additional_value_days",
                ]
                if col in all_columns
            ],
            "📋 Order Details": [
                col
                for col in [
                    "sales_order_type",
                    "sales_order_approval_reason",
                    "sales_doc_approval_status",
                    "sd_document_reason",
                    "reference_sd_document",
                    "reference_sd_document_category",
                    "purchase_order_by_customer",
                    "purchase_order_by_ship_to_party",
                    "customer_purchase_order_type",
                    "customer_purchase_order_suplmnt",
                ]
                if col in all_columns
            ],
            "📊 Status & Processing": [
                col
                for col in [
                    "overall_sd_process_status",
                    "overall_sd_doc_reference_status",
                    "overall_sd_document_rejection_sts",
                    "total_credit_check_status",
                    "total_block_status",
                ]
                if col in all_columns
            ],
            "🌍 International Trade": [
                col
                for col in [
                    "incoterms_classification",
                    "incoterms_version",
                    "incoterms_location1",
                    "incoterms_location2",
                    "incoterms_transfer_location",
                    "tax_departure_country",
                    "vat_registration_country",
                ]
                if col in all_columns
            ],
            "🏷️ Tax Classification": [
                col
                for col in [
                    "customer_tax_classification1",
                    "customer_tax_classification2",
                    "customer_tax_classification3",
                    "customer_tax_classification4",
                    "customer_tax_classification5",
                    "customer_tax_classification6",
                    "customer_tax_classification7",
                    "customer_tax_classification8",
                    "customer_tax_classification9",
                ]
                if col in all_columns
            ],
            "🔧 System & Metadata": [
                col
                for col in [
                    "created_by_user",
                    "sender_business_system_name",
                    "assignment_reference",
                    "corresp_nc_external_reference",
                    "po_corresp_nc_external_reference",
                    "contract_account",
                    "price_list_type",
                    "raw_sap_data",
                    "record_hash",
                    "embedding",
                ]
                if col in all_columns
            ],
        }

        # Filter out empty categories
        return {k: v for k, v in categories.items() if v}

    def _format_schema_for_prompt(self) -> str:
        """
        Format schema with anti-hallucination emphasis.
        """
        categories = self._get_categorized_columns()

        prompt = """
═══════════════════════════════════════════════════════════════
⚠️  CRITICAL: COLUMN NAMES - READ THIS FIRST ⚠️
═══════════════════════════════════════════════════════════════

YOU MUST USE **EXACT** COLUMN NAMES FROM THE LIST BELOW.
DO NOT guess, invent, or modify column names.
DO NOT use common terminology - use ONLY these exact names.

COMMON MISTAKES TO AVOID:
❌ "sales_channel"     → ✅ Use "distribution_channel"
❌ "region"            → ✅ Use "sales_district"
❌ "channel"           → ✅ Use "distribution_channel"
❌ "customer_name"     → ✅ Use "sold_to_party"
❌ "order_date"        → ✅ Use "sales_order_date"
❌ "billing_type"      → ✅ Use "overall_ord_reltd_billg_status"
❌ "delivery_status"   → ✅ Use "overall_delivery_status"

═══════════════════════════════════════════════════════════════
📋 AVAILABLE COLUMNS (EXACT NAMES ONLY)
═══════════════════════════════════════════════════════════════

"""

        for category, columns in categories.items():
            prompt += f"{category}\n"
            for col in columns:
                prompt += f"  • {col}\n"
            prompt += "\n"

        prompt += """
═══════════════════════════════════════════════════════════════
🎯 USAGE RULES
═══════════════════════════════════════════════════════════════

1. Copy column names EXACTLY as shown (case-sensitive)
2. If you need a concept not in the list, respond: "Column not available"
3. When uncertain between columns, choose the most specific one
4. Use table name prefix only when joining (not needed for single table)

EXAMPLE QUERIES:
✅ SELECT sales_district, distribution_channel, COUNT(*)
✅ SELECT sold_to_party, SUM(total_net_amount)
❌ SELECT region, channel, COUNT(*)  -- WRONG: These columns don't exist!

"""

        return prompt

    # ================================================================
    # LAYER 2: COLUMN VALIDATION (ANTI-HALLUCINATION)
    # ================================================================

    def _extract_columns_from_sql(self, sql: str) -> Set[str]:
        """
        Extract all column references from SQL query.

        Handles:
        - SELECT columns
        - WHERE clauses
        - GROUP BY
        - ORDER BY
        - JOINs
        """

        # Remove comments and normalize
        sql_clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        sql_clean = re.sub(r"/\*.*?\*/", "", sql_clean, flags=re.DOTALL)
        sql_clean = sql_clean.lower()

        # Extract potential column names
        # Matches: word characters, underscores (column names)
        potential_cols = re.findall(r"\b([a-z_][a-z0-9_]*)\b", sql_clean)

        # Filter out SQL keywords
        sql_keywords = {
            "select",
            "from",
            "where",
            "group",
            "order",
            "by",
            "as",
            "and",
            "or",
            "not",
            "null",
            "is",
            "in",
            "like",
            "between",
            "case",
            "when",
            "then",
            "else",
            "end",
            "having",
            "distinct",
            "count",
            "sum",
            "avg",
            "max",
            "min",
            "limit",
            "offset",
            "join",
            "left",
            "right",
            "inner",
            "outer",
            "on",
            "true",
            "false",
            "asc",
            "desc",
            "with",
            "date",
            "extract",
            "month",
            "year",
            "sales_orders",  # Table name
        }

        # Get actual column names (case-insensitive comparison)
        actual_columns_lower = {col.lower() for col in self.schema.keys()}

        # Find columns that are referenced but don't exist
        referenced_columns = set()
        for col in potential_cols:
            if col in actual_columns_lower and col not in sql_keywords:
                # Find the actual case-correct name
                for actual_col in self.schema.keys():
                    if actual_col.lower() == col:
                        referenced_columns.add(actual_col)
                        break

        return referenced_columns

    def _validate_columns(self, sql: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all columns in SQL exist in schema.

        Returns:
            (is_valid, invalid_columns, suggestions)
        """

        # Extract columns from SQL
        used_columns = self._extract_columns_from_sql(sql)

        # Check which don't exist
        schema_columns = set(self.schema.keys())
        invalid_columns = []

        # Case-insensitive check for invalid columns
        sql_lower = sql.lower()
        for potential_col in re.findall(r"\b([a-z_][a-z0-9_]{2,})\b", sql_lower):
            if potential_col not in [c.lower() for c in schema_columns]:
                # Check if it's not a SQL keyword or table name
                if potential_col not in {
                    "select",
                    "from",
                    "where",
                    "group",
                    "order",
                    "by",
                    "sales_orders",
                    "count",
                    "sum",
                    "avg",
                    "and",
                    "or",
                    "limit",
                    "offset",
                    "having",
                    "distinct",
                    "union",
                    "all",
                }:
                    # Check if it looks like a column name
                    if "_" in potential_col or len(potential_col) > 5:
                        invalid_columns.append(potential_col)

        invalid_columns = list(set(invalid_columns))  # Deduplicate

        # Get suggestions for each invalid column
        suggestions = []
        for invalid_col in invalid_columns:
            suggestion = self._find_similar_column(invalid_col)
            suggestions.append(suggestion)

        is_valid = len(invalid_columns) == 0

        return is_valid, invalid_columns, suggestions

    # ================================================================
    # LAYER 3: AUTO-CORRECTION WITH FUZZY MATCHING (ANTI-HALLUCINATION)
    # ================================================================

    def _find_similar_column(self, invalid_col: str, threshold: float = 0.6) -> str:
        """
        Find most similar column name using fuzzy matching.

        Args:
            invalid_col: The invalid column name
            threshold: Minimum similarity score (0-1)

        Returns:
            Most similar valid column name or None
        """

        # Common mappings (hardcoded for known issues)
        common_fixes = {
            # Channel/Distribution
            "sales_channel": "distribution_channel",
            "channel": "distribution_channel",
            # Region/District
            "region": "sales_district",
            "district": "sales_district",
            # Customer
            "customer_name": "sold_to_party",
            "customer": "sold_to_party",
            "customer_id": "sold_to_party",
            # Dates
            "order_date": "sales_order_date",
            "date": "sales_order_date",
            # Status fields
            "billing_type": "overall_ord_reltd_billg_status",
            "billing_status": "overall_ord_reltd_billg_status",
            "delivery_status": "overall_delivery_status",
            # Financial
            "amount": "total_net_amount",
            "revenue": "total_net_amount",
            "sales": "total_net_amount",
            "revenue_contribution": "total_net_amount",
            "currency": "transaction_currency",
            # Organization
            "division": "organization_division",
            "org": "sales_organization",
            # Note: 'partner_function' doesn't exist in schema
            # This will be caught and user will be informed via regeneration
        }

        # Check exact matches first
        if invalid_col.lower() in common_fixes:
            return common_fixes[invalid_col.lower()]

        # Fuzzy matching against all columns
        best_match = None
        best_score = threshold

        for valid_col in self.schema.keys():
            # Calculate similarity
            score = SequenceMatcher(
                None, invalid_col.lower(), valid_col.lower()
            ).ratio()

            if score > best_score:
                best_score = score
                best_match = valid_col

        return best_match

    def _auto_correct_sql(
        self, sql: str, invalid_columns: List[str], suggestions: List[str]
    ) -> Tuple[str, List[Dict]]:
        """
        Automatically correct SQL by replacing invalid columns.

        Returns:
            (corrected_sql, list_of_corrections)
        """

        corrected_sql = sql
        corrections = []

        for invalid_col, suggestion in zip(invalid_columns, suggestions):
            if suggestion:
                # Replace with case-insensitive regex
                pattern = re.compile(re.escape(invalid_col), re.IGNORECASE)
                corrected_sql = pattern.sub(suggestion, corrected_sql)

                corrections.append(
                    {
                        "from": invalid_col,
                        "to": suggestion,
                        "confidence": "high"
                        if invalid_col.lower() in ["sales_channel", "region", "channel"]
                        else "medium",
                    }
                )

                self.logger.info(
                    "column_auto_corrected", from_col=invalid_col, to_col=suggestion
                )

        return corrected_sql, corrections

    # ================================================================
    # LAYER 4: ERROR FEEDBACK & REGENERATION (ANTI-HALLUCINATION)
    # ================================================================

    def _regenerate_with_error_feedback(
        self,
        query: str,
        failed_sql: str,
        invalid_columns: List[str],
        schema_prompt: str,
    ) -> str:
        """
        Regenerate SQL with explicit error feedback to LLM.
        """

        error_prompt = f"""
⚠️ PREVIOUS ATTEMPT FAILED ⚠️

You generated SQL with INVALID column names:
{", ".join(invalid_columns)}

These columns DO NOT EXIST in the table!

FAILED SQL:
{failed_sql}

{schema_prompt}

TASK: Regenerate the query using ONLY columns from the AVAILABLE COLUMNS list above.
Do NOT use: {", ".join(invalid_columns)}

Original question: {query}

Generate corrected SQL (ONLY the SQL query, no explanations):
"""

        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a SQL expert. Fix the column names using only the provided schema.",
                },
                {"role": "user", "content": error_prompt},
            ],
            temperature=0,
            max_tokens=1500,
        )

        sql = response.choices[0].message.content.strip()
        sql = self._extract_sql_from_response(sql)

        self.logger.info("sql_regenerated_after_error")

        return sql

    def _extract_sql_from_response(self, response: str) -> str:
        """Extract clean SQL from LLM response."""
        sql = response.replace("```sql", "").replace("```", "").strip()

        # If LLM still adds explanatory text, try to extract just the SQL
        if not sql.upper().startswith(("SELECT", "WITH", "(")):
            lines = sql.split("\n")
            for line in lines:
                line = line.strip()
                if line.upper().startswith(("SELECT", "WITH", "(")):
                    sql = line
                    break

        return sql

    # ================================================================
    # SCHEMA FORMATTING FOR LLM (LEGACY - KEPT FOR COMPATIBILITY)
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
    # SQL GENERATION WITH MULTI-LAYER VALIDATION
    # ================================================================

    def _generate_sql(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate SQL with multi-layer validation.

        Layers:
        1. Enhanced prompt with categorized columns (prevention)
        2. Column validation after generation (detection)
        3. Auto-correction with fuzzy matching (correction)
        4. Regeneration with error feedback (learning)
        """
        from core.graphs.conversation_utils import format_conversation_context

        self.logger.info("generating_sql_with_validation", query=query)

        # Build enhanced prompt with categorized columns (Layer 1)
        schema_prompt = self._format_schema_for_prompt()

        similar_examples = self.few_shot_store.find_similar_examples(
            query=query, top_k=2
        )

        few_shot_prompt = self.few_shot_store.format_examples_for_prompt(
            similar_examples
        )

        if similar_examples:
            self.logger.info(
                "few_shot_examples_retrieved",
                count=len(similar_examples),
                questions=[e.question for e in similar_examples],
                categories=[e.category for e in similar_examples],
            )

        conversation_context = ""
        if context and context.get("conversation_history"):
            conversation_context = format_conversation_context(
                context["conversation_history"],
                max_turns=2,
            )

            prompt = f"""You are a PostgreSQL query generator.
            DATABASE SCHEMA:
                {schema_prompt}
                {few_shot_prompt}

                USER QUESTION:
                    {query}
                    RULES:
                        1. Return ONLY the SQL query
                        2. NO explanations, descriptions, or comments
                        3. NO markdown formatting or code blocks
                        4. Start directly with SELECT or WITH
                        5. Query must be read-only (SELECT/WITH only)
                        6. Use the sales_orders table
                        7. Use EXACT column names from the schema above
                        8. LEARN from the example queries above - use similar patterns
                        ⚠️ CRITICAL POSTGRESQL SYNTAX - UNION QUERIES:

                        - ALWAYS wrap each SELECT in parentheses when using UNION with ORDER BY/LIMIT
                        - ✅ CORRECT: (SELECT ... ORDER BY x DESC LIMIT 1) UNION ALL (SELECT ... ORDER BY x ASC LIMIT 1)
                        - ❌ WRONG:   SELECT ... ORDER BY x DESC LIMIT 1 UNION ALL SELECT ... ORDER BY x ASC LIMIT 1

                        OTHER SYNTAX RULES:
                        - For CTEs (WITH clause), use proper syntax: WITH cte AS (...) SELECT ...
                        - Always use explicit type casting when needed: ::integer, ::date, etc.
                        - Use DATE_TRUNC for time-based aggregations (see examples above)
                        - Use window functions for share/percentage calculations (see examples above)

                        Now generate ONLY the SQL query for the user's question (no explanations):
                        """

        # Generate SQL from LLM
        response = self.llm.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )

        sql = response.choices[0].message.content.strip()
        sql = self._extract_sql_from_response(sql)

        # === LAYER 2: VALIDATION ===

        is_valid, invalid_columns, suggestions = self._validate_columns(sql)

        if not is_valid:
            self.logger.warning(
                "invalid_columns_detected",
                invalid=invalid_columns,
                suggestions=suggestions,
            )

            # === LAYER 3: AUTO-CORRECTION ===
            sql, corrections = self._auto_correct_sql(sql, invalid_columns, suggestions)

            if corrections:
                self.logger.info("sql_auto_corrected", corrections=corrections)

            # Re-validate after correction (even if no corrections were made)
            is_valid_now, still_invalid, _ = self._validate_columns(sql)

            if not is_valid_now:
                # === LAYER 4: REGENERATION WITH FEEDBACK ===
                self.logger.error(
                    "auto_correction_failed",
                    still_invalid=still_invalid,
                    corrections_attempted=len(corrections) if corrections else 0,
                )

                # Try one more time with explicit error message
                sql = self._regenerate_with_error_feedback(
                    query, sql, still_invalid, schema_prompt
                )

        self.logger.info("sql_generated_successfully", sql_length=len(sql))

        return sql

    # ================================================================
    # VALIDATION
    # ================================================================

    def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Policy validation - check for dangerous SQL operations.
        Returns dict with 'valid' boolean and 'reason' string.
        """
        sql_upper = sql.upper()

        # List of forbidden operations
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "INSERT",
            "UPDATE",
            "ALTER",
            "CREATE",
            "GRANT",
            "REVOKE",
        ]

        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return {
                    "valid": False,
                    "reason": f"SQL contains forbidden keyword: {keyword}",
                }

        # Check it starts with SELECT or WITH
        if not (
            sql_upper.strip().startswith("SELECT")
            or sql_upper.strip().startswith("WITH")
            or sql_upper.strip().startswith("(")
        ):  # Wrapped queries
            return {
                "valid": False,
                "reason": "SQL must start with SELECT, WITH, or be a wrapped query",
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
