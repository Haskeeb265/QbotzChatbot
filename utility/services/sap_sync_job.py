#!/usr/bin/env python3
"""
Standalone SAP Sync Runner
Run this script independently to sync SAP data to PostgreSQL

Usage:
    # Full sync
    python run_sap_sync.py

    # With filters
    python run_sap_sync.py --filter "SalesOrderDate gt datetime'2024-01-01T00:00:00'"

    # Include embeddings
    python run_sap_sync.py --embed

    # Dry run (no database changes)
    python run_sap_sync.py --dry-run
"""

import argparse
import sys
from datetime import datetime
from typing import Any, Dict

from core.storage.embedding.embedding_service import EmbeddingService
from core.storage.sap_sync.db_queries import DataAccess, DatabaseConnection
from core.storage.sap_sync.sap_sync import SAPSyncService
from utility.observability.logger import get_logger

logger = get_logger("sap_sync_runner")


class SAPSyncRunner:
    """Orchestrates SAP sync with optional embedding generation"""

    def __init__(self):
        self.sync_service = SAPSyncService()
        self.embedding_service = EmbeddingService()
        self.db_access = DataAccess()

    def run(
        self,
        filters: str = None,
        generate_embeddings: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Run complete sync pipeline

        Args:
            filters: SAP OData filter string
            generate_embeddings: Whether to generate embeddings after sync
            dry_run: If True, don't commit changes

        Returns:
            Dict with sync and embedding stats
        """
        start_time = datetime.utcnow()

        logger.info(
            "sync_run_starting",
            filters=filters,
            generate_embeddings=generate_embeddings,
            dry_run=dry_run,
        )

        result = {
            "success": False,
            "sync_stats": {},
            "embedding_stats": {},
            "duration_seconds": 0,
            "timestamp": start_time.isoformat(),
        }

        try:
            # Step 1: Ensure schema exists
            if not dry_run:
                self._ensure_schema()

            # Step 2: Sync SAP data
            sync_stats = self._run_sync(filters, dry_run)
            result["sync_stats"] = sync_stats

            # Step 3: Generate embeddings (if requested)
            if generate_embeddings and not dry_run:
                embedding_stats = self._run_embeddings()
                result["embedding_stats"] = embedding_stats

            # Step 4: Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            result["duration_seconds"] = round(duration, 2)
            result["success"] = True

            logger.info("sync_run_completed", **result)

            return result

        except Exception as e:
            logger.error("sync_run_failed", error=str(e), error_type=type(e).__name__)
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            return result

    def _ensure_schema(self) -> None:
        """Initialize database schema if needed"""
        logger.info("checking_schema")
        try:
            self.db_access.initialize_schema()
            logger.info("schema_ready")
        except Exception as e:
            logger.error("schema_check_failed", error=str(e))
            raise

    def _run_sync(self, filters: str, dry_run: bool) -> Dict[str, Any]:
        """Run SAP sync"""
        logger.info("running_sap_sync", filters=filters, dry_run=dry_run)

        if dry_run:
            logger.warning("dry_run_mode_enabled_skipping_sync")
            return {
                "inserted": 0,
                "updated": 0,
                "unchanged": 0,
                "errors": 0,
                "dry_run": True,
            }

        stats = self.sync_service.sync_sales_orders(filters=filters)

        logger.info("sap_sync_completed", **stats)
        return stats

    def _run_embeddings(self) -> Dict[str, Any]:
        """Generate embeddings for synced data"""
        logger.info("running_embedding_generation")

        stats = self.embedding_service.embed_all_sales_orders()

        logger.info("embedding_generation_completed", **stats)
        return stats

    def get_health_status(self) -> Dict[str, Any]:
        """Check database health"""
        return self.db_access.health_check()


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="SAP to PostgreSQL Sync Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full sync
  python run_sap_sync.py

  # Sync with date filter
  python run_sap_sync.py --filter "SalesOrderDate gt datetime'2024-01-01T00:00:00'"

  # Sync and generate embeddings
  python run_sap_sync.py --embed

  # Check database health
  python run_sap_sync.py --health-check

  # Dry run (test without committing)
  python run_sap_sync.py --dry-run
        """,
    )

    parser.add_argument(
        "--filter",
        type=str,
        help="SAP OData filter expression",
        default=None,
    )

    parser.add_argument(
        "--embed",
        action="store_true",
        help="Generate embeddings after sync",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without committing changes",
    )

    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Check database health and exit",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def print_summary(result: Dict[str, Any]) -> None:
    """Print human-readable summary"""
    print("\n" + "=" * 60)
    print("SAP SYNC SUMMARY")
    print("=" * 60)

    if result.get("success"):
        print("✅ Status: SUCCESS")
    else:
        print("❌ Status: FAILED")
        if result.get("error"):
            print(f"Error: {result['error']}")
        return

    # Sync stats
    sync_stats = result.get("sync_stats", {})
    if sync_stats:
        print("\n📊 Sync Statistics:")
        print(f"  - Inserted: {sync_stats.get('inserted', 0)}")
        print(f"  - Updated: {sync_stats.get('updated', 0)}")
        print(f"  - Unchanged: {sync_stats.get('unchanged', 0)}")
        print(f"  - Errors: {sync_stats.get('errors', 0)}")

        total = sum(
            [
                sync_stats.get("inserted", 0),
                sync_stats.get("updated", 0),
                sync_stats.get("unchanged", 0),
            ]
        )
        print(f"  - Total Processed: {total}")

    # Embedding stats
    embedding_stats = result.get("embedding_stats", {})
    if embedding_stats:
        print("\n🔢 Embedding Statistics:")
        print(f"  - Embedded: {embedding_stats.get('embedded', 0)}")
        print(f"  - Skipped: {embedding_stats.get('skipped', 0)}")
        print(f"  - Errors: {embedding_stats.get('errors', 0)}")

    # Duration
    duration = result.get("duration_seconds", 0)
    print(f"\n⏱️  Duration: {duration} seconds")

    # Timestamp
    timestamp = result.get("timestamp", "")
    print(f"🕐 Timestamp: {timestamp}")

    print("=" * 60 + "\n")


def main():
    """Main entry point"""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize runner
    runner = SAPSyncRunner()

    try:
        # Health check mode
        if args.health_check:
            print("\n🏥 Running Health Check...")
            health = runner.get_health_status()

            print("\n" + "=" * 60)
            print("DATABASE HEALTH STATUS")
            print("=" * 60)
            print(f"Status: {health.get('status', 'unknown').upper()}")

            if health.get("status") == "healthy":
                print(f"Total Records: {health.get('sales_count', 0):,}")
                print(f"Latest Sync: {health.get('latest_sync', 'N/A')}")

                date_range = health.get("date_range", {})
                print(f"Earliest Order: {date_range.get('earliest', 'N/A')}")
                print(f"Latest Order: {date_range.get('latest', 'N/A')}")
            else:
                print(f"Error: {health.get('error', 'Unknown error')}")

            print("=" * 60 + "\n")
            return 0 if health.get("status") == "healthy" else 1

        # Normal sync mode
        print("\n🔄 Starting SAP Sync...")
        if args.dry_run:
            print("⚠️  DRY RUN MODE - No changes will be committed\n")

        result = runner.run(
            filters=args.filter,
            generate_embeddings=args.embed,
            dry_run=args.dry_run,
        )

        # Print summary
        print_summary(result)

        # Exit code
        return 0 if result.get("success") else 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user")
        logger.warning("sync_interrupted_by_user")
        return 130

    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        logger.error("fatal_error", error=str(e))
        return 1

    finally:
        # Cleanup
        try:
            DatabaseConnection.close_pool()
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())
