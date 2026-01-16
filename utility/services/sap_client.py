import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Optional, Any
from datetime import datetime
import time

from utility.observability.logger import get_logger
from config.settings import settings

logger = get_logger("sap_client")


class SAPClient:
    
    def __init__(self):
        self.base_url = settings.SAP_BASE_URL
        self.auth = HTTPBasicAuth(settings.SAP_USERNAME, settings.SAP_PASSWORD)
        self.client = settings.SAP_CLIENT
        self.session = requests.Session()
        self.session.auth = self.auth

        logger.info(
            "sap_client_initialized",
            base_url=self.base_url,
            client=self.client,
        )

    def fetch_sales_orders(
        self, filters: Optional[str] = None, top: int = 1000, skip: int = 0
    ) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/API_SALES_ORDER_SRV/A_SalesOrder"
        params = {
            "client": self.client,
            "$format": "json",
            "$top": top,
            "$skip": skip,
        }

        if filters:
            params["$filter"] = filters

        logger.info(
            "sap_request_starting",
            endpoint="A_SalesOrder",
            top=top,
            skip=skip,
            filters=filters,
        )
        start_time = datetime.utcnow()

        try:
            response = self.session.get(endpoint, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            record_count = len(data.get("d", {}).get("results", []))

            logger.info(
                "sap_request_completed",
                records_fetched=record_count,
                duration_ms=duration_ms,
                response_size_mb=round(len(response.content) / 1024 / 1024, 2),
            )

            return data

        except requests.exceptions.Timeout:
            logger.error(
                "sap_request_timeout",
                endpoint=endpoint,
                timeout_seconds=60,
            )
            raise

        except requests.exceptions.ConnectionError as e:
            logger.error(
                "sap_connection_failed",
                error=str(e),
                hint="Check VPN connection",
            )
            raise

        except requests.exceptions.HTTPError as e:
            logger.error(
                "sap_http_error",
                status_code=response.status_code,
                error=str(e),
            )
            raise

    def fetch_all_sales_orders(self, filters: Optional[str] = None) -> List[Dict[str, Any]]:
        all_records = []
        batch_size = 1000
        skip = 0

        logger.info(
            "sap_full_fetch_starting",
            batch_size=batch_size,
            filter=filters,
        )

        while True:
            # Fetch one batch
            response = self.fetch_sales_orders(
                filters=filters,
                top=batch_size,
                skip=skip,
            )

            results = response.get("d", {}).get("results", [])

            if not results:
                # No more records
                logger.info(
                    "sap_full_fetch_completed",
                    total_records=len(all_records),
                    batches_fetched=skip // batch_size + 1,
                )
                break

            all_records.extend(results)

            # Check if we got fewer records than requested (last batch)
            if len(results) < batch_size:
                logger.info(
                    "sap_full_fetch_completed",
                    total_records=len(all_records),
                    batches_fetched=skip // batch_size + 1,
                )
                break

            skip += batch_size

            # Rate limiting: Don't overwhelm SAP
            time.sleep(0.5)  # 500ms delay between requests

        return all_records

    def test_connection(self) -> bool:
        try:
            self.fetch_sales_orders(top=1)
            return True
        except Exception as e:
            logger.error(
                "sap_connection_failed",
                error=str(e),
            )
            return False
