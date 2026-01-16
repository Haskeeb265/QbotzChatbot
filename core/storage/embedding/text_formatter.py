from typing import Dict, Any
from utility.observability.logger import get_logger

logger = get_logger("text_formatter")


class SalesOrderFormatter:
    STATUS_MAP = {"C": "completed", "A": "approved", "B": "blocked", "": "pending"}

    @staticmethod
    def to_searchable_text(record: Dict[str, Any]) -> str:
        parts = []

        # Basic identification
        if record.get("sales_order"):
            parts.append(f"Sales order {record['sales_order']}")

        if record.get("sold_to_party"):
            parts.append(f"for customer {record['sold_to_party']}")

        # Financial information
        if record.get("total_net_amount"):
            currency = record.get("transaction_currency", "")
            parts.append(f"Total amount {record['total_net_amount']} {currency}")

        # Geographic information
        if record.get("sales_district"):
            parts.append(f"Sales district {record['sales_district']}")

        if record.get("sales_office"):
            parts.append(f"office {record['sales_office']}")

        # Status (with human-readable translation)
        status_code = record.get("overall_delivery_status", "")
        status_text = SalesOrderFormatter.STATUS_MAP.get(status_code, status_code)
        if status_text:
            parts.append(f"Status: {status_text}")

        # Date information
        if record.get("sales_order_date"):
            parts.append(f"Order date: {record['sales_order_date']}")

        # Type information
        if record.get("sales_order_type"):
            parts.append(f"Type: {record['sales_order_type']}")

        return ". ".join(parts) + "."

    @staticmethod
    def validate_record(record: Dict[str, Any]) -> bool:

        required_fields = ["sales_order"]

        for field in required_fields:
            if not record.get(field):
                logger.warning(
                    "invalid_record",
                    missing_field=field,
                    sales_order=record.get("sales_order"),
                )
                return False

        return True
