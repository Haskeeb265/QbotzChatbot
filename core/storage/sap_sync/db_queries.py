import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from config.settings import settings
from utility.observability.logger import get_logger


logger = get_logger("db_queries")


class DatabaseConnection:
    """Connection pool manager"""

    _pool: Optional[pool.SimpleConnectionPool] = None

    @classmethod
    def initialize_pool(cls) -> None:
        """Call this once at application startup"""
        if cls._pool is not None:
            return

        logger.info(
            "database_pool_initializing",
            min_connections=1,
            max_connections=settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW,
        )

        cls._pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW,
            dsn=settings.DATABASE_URL,
        )

        # Enable pgvector extension
        conn = cls.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()
                logger.info("pgvector_extension_enabled")
        finally:
            cls.return_connection(conn)

    @classmethod
    def get_connection(cls):
        if cls._pool is None:
            cls.initialize_pool()
        return cls._pool.getconn()

    @classmethod
    def return_connection(cls, conn) -> None:
        cls._pool.putconn(conn)

    @classmethod
    def close_pool(cls) -> None:
        if cls._pool:
            cls._pool.closeall()
            logger.info("database_pool_closed")


class DataAccess:
    """Main database access layer"""

    def __init__(self) -> None:
        self.logger = logger

    def initialize_schema(self) -> None:
        """
        Create sales_orders table with ALL 91 SAP fields

        NAMING CONVENTION:
        - SAP: PascalCase (SalesOrderType)
        - PostgreSQL: snake_case (sales_order_type)

        TYPE MAPPING:
        - SAP strings → VARCHAR
        - Money → DECIMAL(15,2)
        - SAP /Date(...)/ → DATE or TIMESTAMP
        - SAP booleans → BOOLEAN
        """
        conn = DatabaseConnection.get_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sales_orders (
                        sales_order VARCHAR(10) PRIMARY KEY,

                        sales_order_type VARCHAR(4),
                        sales_organization VARCHAR(4),
                        distribution_channel VARCHAR(2),
                        organization_division VARCHAR(2),
                        sales_group VARCHAR(3),
                        sales_office VARCHAR(4),
                        sales_district VARCHAR(6),

                        sold_to_party VARCHAR(10),

                        creation_date DATE,
                        last_change_date DATE,
                        sales_order_date DATE,
                        customer_purchase_order_date DATE,
                        pricing_date DATE,
                        requested_delivery_date DATE,
                        fixed_value_date DATE,
                        billing_document_date DATE,
                        services_rendered_date DATE,
                        last_change_date_time TIMESTAMP,
                        external_doc_last_change_date_time TIMESTAMP,

                        created_by_user VARCHAR(12),
                        sender_business_system_name VARCHAR(60),

                        external_document_id VARCHAR(40),
                        purchase_order_by_customer VARCHAR(35),
                        purchase_order_by_ship_to_party VARCHAR(35),
                        customer_purchase_order_type VARCHAR(4),
                        customer_purchase_order_suplmnt VARCHAR(4),

                        total_net_amount DECIMAL(15,2),
                        transaction_currency VARCHAR(5),
                        price_detn_exchange_rate DECIMAL(12,5),
                        accounting_exchange_rate DECIMAL(12,5),

                        overall_delivery_status VARCHAR(1),
                        total_block_status VARCHAR(1),
                        overall_ord_reltd_billg_status VARCHAR(1),
                        overall_sd_doc_reference_status VARCHAR(1),
                        overall_sd_process_status VARCHAR(1),
                        total_credit_check_status VARCHAR(1),
                        overall_total_delivery_status VARCHAR(1),
                        overall_sd_document_rejection_sts VARCHAR(1),
                        sales_doc_approval_status VARCHAR(1),

                        shipping_condition VARCHAR(2),
                        complete_delivery_is_defined BOOLEAN,
                        shipping_type VARCHAR(2),
                        header_billing_block_reason VARCHAR(2),
                        delivery_block_reason VARCHAR(2),
                        delivery_date_type_rule VARCHAR(1),

                        incoterms_classification VARCHAR(3),
                        incoterms_transfer_location VARCHAR(28),
                        incoterms_location1 VARCHAR(70),
                        incoterms_location2 VARCHAR(70),
                        incoterms_version VARCHAR(4),

                        customer_price_group VARCHAR(2),
                        price_list_type VARCHAR(2),
                        customer_payment_terms VARCHAR(4),
                        payment_method VARCHAR(1),

                        billing_plan VARCHAR(10),

                        assignment_reference VARCHAR(18),
                        reference_sd_document VARCHAR(10),
                        reference_sd_document_category VARCHAR(4),
                        accounting_doc_external_reference VARCHAR(16),
                        corresp_nc_external_reference VARCHAR(12),
                        po_corresp_nc_external_reference VARCHAR(12),

                        customer_account_assignment_group VARCHAR(2),
                        customer_condition_group1 VARCHAR(2),
                        customer_condition_group2 VARCHAR(2),
                        customer_condition_group3 VARCHAR(2),
                        customer_condition_group4 VARCHAR(2),
                        customer_condition_group5 VARCHAR(2),
                        customer_group VARCHAR(2),
                        additional_customer_group1 VARCHAR(3),
                        additional_customer_group2 VARCHAR(3),
                        additional_customer_group3 VARCHAR(3),
                        additional_customer_group4 VARCHAR(3),
                        additional_customer_group5 VARCHAR(3),

                        customer_tax_classification1 VARCHAR(1),
                        customer_tax_classification2 VARCHAR(1),
                        customer_tax_classification3 VARCHAR(1),
                        customer_tax_classification4 VARCHAR(1),
                        customer_tax_classification5 VARCHAR(1),
                        customer_tax_classification6 VARCHAR(1),
                        customer_tax_classification7 VARCHAR(1),
                        customer_tax_classification8 VARCHAR(1),
                        customer_tax_classification9 VARCHAR(1),

                        tax_departure_country VARCHAR(3),
                        vat_registration_country VARCHAR(3),

                        sd_document_reason VARCHAR(3),
                        sales_order_approval_reason VARCHAR(4),
                        sls_doc_is_rlvt_for_proof_of_deliv BOOLEAN,

                        contract_account VARCHAR(12),
                        additional_value_days VARCHAR(2),

                        record_hash VARCHAR(32),
                        first_synced_at TIMESTAMP DEFAULT NOW(),
                        last_updated_at TIMESTAMP DEFAULT NOW(),

                        raw_sap_data JSONB,
                        embedding vector(768)
                    );
                    """
                )

                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_sales_order_date ON sales_orders(sales_order_date);",
                    "CREATE INDEX IF NOT EXISTS idx_billing_date ON sales_orders(billing_document_date);",
                    "CREATE INDEX IF NOT EXISTS idx_sales_district ON sales_orders(sales_district);",
                    "CREATE INDEX IF NOT EXISTS idx_sales_office ON sales_orders(sales_office);",
                    "CREATE INDEX IF NOT EXISTS idx_sales_organization ON sales_orders(sales_organization);",
                    "CREATE INDEX IF NOT EXISTS idx_sold_to_party ON sales_orders(sold_to_party);",
                    "CREATE INDEX IF NOT EXISTS idx_sales_order_type ON sales_orders(sales_order_type);",
                    "CREATE INDEX IF NOT EXISTS idx_distribution_channel ON sales_orders(distribution_channel);",
                    "CREATE INDEX IF NOT EXISTS idx_organization_division ON sales_orders(organization_division);",
                    "CREATE INDEX IF NOT EXISTS idx_region_date ON sales_orders(sales_district, sales_order_date);",
                    "CREATE INDEX IF NOT EXISTS idx_customer_date ON sales_orders(sold_to_party, sales_order_date);",
                    "CREATE INDEX IF NOT EXISTS idx_raw_sap_gin ON sales_orders USING gin(raw_sap_data);",
                    "CREATE INDEX IF NOT EXISTS idx_embedding ON sales_orders USING hnsw (embedding vector_cosine_ops);",
                ]

                for index_sql in indexes:
                    cur.execute(index_sql)

                conn.commit()

                self.logger.info(
                    "schema_initialized",
                    table="sales_orders",
                    columns=91,
                    indexes=len(indexes),
                )

        except Exception as e:
            conn.rollback()
            self.logger.error("schema_initialization_failed", error=e)
            raise

        finally:
            DatabaseConnection.return_connection(conn)

    def get_sales_schema(self) -> Dict[str, str]:
        """Returns column names and types for SQL Agent"""
        conn = DatabaseConnection.get_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        column_name,
                        data_type,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM information_schema.columns
                    WHERE table_name = 'sales_orders'
                      AND column_name NOT IN ('raw_sap_data', 'embedding', 'record_hash')
                    ORDER BY ordinal_position;
                    """
                )

                schema: Dict[str, str] = {}

                for col_name, data_type, char_len, precision, scale in cur.fetchall():
                    if char_len:
                        schema[col_name] = f"{data_type.upper()}({char_len})"
                    elif precision:
                        schema[col_name] = f"DECIMAL({precision},{scale})"
                    else:
                        schema[col_name] = data_type.upper()

                self.logger.info("schema_fetched", column_count=len(schema))
                return schema

        finally:
            DatabaseConnection.return_connection(conn)

    def execute_sql(
        self,
        sql_query: str,
        params: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """Execute SQL query safely"""
        conn = DatabaseConnection.get_connection()
        start_time = datetime.utcnow()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if settings.ENABLE_QUERY_LOGGING:
                    self.logger.debug("sql_executing", query=sql_query[:200])

                cur.execute(sql_query, params)
                results = cur.fetchall()

                duration_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )

                self.logger.info(
                    "sql_executed",
                    rows_returned=len(results),
                    duration_ms=duration_ms,
                )

                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(
                "sql_execution_failed",
                error=e,
                query=sql_query[:200],
            )
            raise

        finally:
            DatabaseConnection.return_connection(conn)

    def health_check(self) -> Dict[str, Any]:
        """Database health monitoring"""
        try:
            result = self.execute_sql(
                """
                SELECT
                    COUNT(*) AS total_records,
                    MAX(last_updated_at) AS latest_sync,
                    MIN(sales_order_date) AS earliest_order,
                    MAX(sales_order_date) AS latest_order
                FROM sales_orders;
                """
            )

            row = result[0]

            return {
                "status": "healthy",
                "sales_count": row["total_records"],
                "latest_sync": (
                    row["latest_sync"].isoformat() if row["latest_sync"] else None
                ),
                "date_range": {
                    "earliest": (
                        row["earliest_order"].isoformat()
                        if row["earliest_order"]
                        else None
                    ),
                    "latest": (
                        row["latest_order"].isoformat() if row["latest_order"] else None
                    ),
                },
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


def parse_sap_date(sap_date_str: str) -> Optional[datetime]:
    """Convert SAP /Date(milliseconds)/ format to datetime"""
    if not sap_date_str or sap_date_str == "null":
        return None

    try:
        timestamp_str = sap_date_str.replace("/Date(", "").replace(")/", "")

        if "+" in timestamp_str or "-" in timestamp_str:
            timestamp_str = timestamp_str.split("+")[0].split("-")[0]

        return datetime.fromtimestamp(int(timestamp_str) / 1000)

    except Exception as e:
        logger.warning(
            "date_parse_failed",
            sap_date=sap_date_str,
            error=str(e),
        )
        return None


def calculate_record_hash(sap_record: Dict[str, Any]) -> str:
    """Create MD5 hash of critical SAP fields"""
    fields = [
        sap_record.get("SalesOrder", ""),
        sap_record.get("TotalNetAmount", ""),
        sap_record.get("OverallDeliveryStatus", ""),
        sap_record.get("LastChangeDateTime", ""),
        sap_record.get("OverallSDProcessStatus", ""),
    ]

    hash_string = "|".join(str(f) for f in fields)
    return hashlib.md5(hash_string.encode()).hexdigest()
