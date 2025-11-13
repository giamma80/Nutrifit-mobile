"""Setup MongoDB indexes for optimal query performance.

This script creates all necessary indexes for the MongoDB collections
used by the Nutrifit backend persistence layer.

Collections:
- meals: Meal domain documents
- nutritional_profiles: NutritionalProfile domain documents
- activity_events: ActivityEvent minute-level documents
- health_snapshots: HealthSnapshot cumulative documents

Usage:
    uv run python scripts/setup_mongodb_indexes.py

Environment Variables:
    MONGODB_URI: MongoDB connection string (required)
    MONGODB_DATABASE: Database name (default: nutrifit)
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from infrastructure.config import get_mongodb_uri, get_mongodb_database

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logging.debug(f"Loaded environment from: {env_path}")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def create_meal_indexes(db: AsyncIOMotorDatabase[Dict[str, Any]]) -> None:
    """Create indexes for meals collection.

    Indexes:
    - _id: unique (automatic)
    - user_id + created_at: list meals by user with date sorting
    - user_id + meal_date: query meals for specific dates
    """
    collection = db["meals"]
    logger.info("Creating indexes for 'meals' collection...")

    # Compound index for listing meals by user (most common query)
    await collection.create_index(
        [("user_id", 1), ("created_at", -1)],
        name="idx_user_created",
        background=True,
    )
    logger.info("  ✓ Created index: user_id + created_at (descending)")

    # Index for date-based queries
    await collection.create_index(
        [("user_id", 1), ("meal_date", 1)],
        name="idx_user_date",
        background=True,
    )
    logger.info("  ✓ Created index: user_id + meal_date")

    # Index for meal_date range queries
    await collection.create_index(
        [("meal_date", 1)],
        name="idx_meal_date",
        background=True,
    )
    logger.info("  ✓ Created index: meal_date")


async def create_profile_indexes(db: AsyncIOMotorDatabase[Dict[str, Any]]) -> None:
    """Create indexes for nutritional_profiles collection.

    Indexes:
    - _id: unique UUID (automatic)
    - user_id: unique, lookup by user (most common query)
    """
    collection = db["nutritional_profiles"]
    logger.info("Creating indexes for 'nutritional_profiles' collection...")

    # Check if user_id index already exists
    existing_indexes = await collection.list_indexes().to_list(length=None)
    user_id_exists = any(
        "user_id" in idx.get("key", {}) and idx.get("unique", False) for idx in existing_indexes
    )

    if not user_id_exists:
        # Unique index on user_id (one profile per user)
        await collection.create_index(
            [("user_id", 1)],
            name="idx_user_unique",
            unique=True,
            background=True,
        )
        logger.info("  ✓ Created unique index: user_id")
    else:
        logger.info("  ℹ️  Unique index on user_id already exists (skipped)")


async def create_activity_event_indexes(db: AsyncIOMotorDatabase[Dict[str, Any]]) -> None:
    """Create indexes for activity_events collection.

    Indexes:
    - _id: unique compound key (user_id + ts) (automatic via document design)
    - user_id + ts: range queries by timestamp
    - user_id + date: daily aggregations
    """
    collection = db["activity_events"]
    logger.info("Creating indexes for 'activity_events' collection...")

    # Compound index for timestamp range queries
    await collection.create_index(
        [("user_id", 1), ("ts", 1)],
        name="idx_user_ts",
        background=True,
    )
    logger.info("  ✓ Created index: user_id + ts (ascending)")

    # Index for user-specific queries (covers most common use case)
    await collection.create_index(
        [("user_id", 1)],
        name="idx_user",
        background=True,
    )
    logger.info("  ✓ Created index: user_id")


async def create_health_snapshot_indexes(db: AsyncIOMotorDatabase[Dict[str, Any]]) -> None:
    """Create indexes for health_snapshots collection.

    Indexes:
    - _id: unique compound key (user_id + date + timestamp) (automatic)
    - user_id + date + timestamp: query deltas, get latest snapshot
    - user_id + date: daily totals aggregation
    """
    collection = db["health_snapshots"]
    logger.info("Creating indexes for 'health_snapshots' collection...")

    # Compound index for delta queries (chronological order)
    await collection.create_index(
        [("user_id", 1), ("date", 1), ("timestamp", 1)],
        name="idx_user_date_ts_asc",
        background=True,
    )
    logger.info("  ✓ Created index: user_id + date + timestamp (ascending)")

    # Compound index for latest snapshot queries (reverse chronological)
    await collection.create_index(
        [("user_id", 1), ("date", 1), ("timestamp", -1)],
        name="idx_user_date_ts_desc",
        background=True,
    )
    logger.info("  ✓ Created index: user_id + date + timestamp (descending)")

    # Index for date-based aggregations
    await collection.create_index(
        [("user_id", 1), ("date", 1)],
        name="idx_user_date",
        background=True,
    )
    logger.info("  ✓ Created index: user_id + date")


async def list_existing_indexes(db: AsyncIOMotorDatabase[Dict[str, Any]]) -> None:
    """List all existing indexes for verification.

    Args:
        db: MongoDB database instance
    """
    logger.info("\n" + "=" * 60)
    logger.info("Existing Indexes Summary")
    logger.info("=" * 60)

    collections = [
        "meals",
        "nutritional_profiles",
        "activity_events",
        "health_snapshots",
    ]

    for coll_name in collections:
        collection = db[coll_name]
        indexes = await collection.list_indexes().to_list(length=None)

        logger.info(f"\n{coll_name}:")
        for idx in indexes:
            name = idx.get("name", "unknown")
            keys = idx.get("key", {})
            unique = " (unique)" if idx.get("unique", False) else ""
            keys_str = ", ".join(f"{k}:{v}" for k, v in keys.items())
            logger.info(f"  • {name}: [{keys_str}]{unique}")


async def setup_all_indexes() -> None:
    """Setup all MongoDB indexes for the Nutrifit backend.

    Creates indexes for all collections used by the persistence layer.
    Runs in background mode to avoid blocking operations.
    """
    # Get MongoDB connection
    uri = get_mongodb_uri()
    if not uri:
        logger.error("MONGODB_URI not configured!")
        logger.error("Set MONGODB_URI environment variable with connection string.")
        sys.exit(1)

    database_name = get_mongodb_database()
    logger.info(f"Connecting to MongoDB: {database_name}")

    client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(uri)
    db = client[database_name]

    try:
        # Verify connection
        await client.admin.command("ping")
        logger.info("✓ Connected to MongoDB successfully\n")

        # Create indexes for each collection
        await create_meal_indexes(db)
        await create_profile_indexes(db)
        await create_activity_event_indexes(db)
        await create_health_snapshot_indexes(db)

        logger.info("\n✅ All indexes created successfully!")

        # List all indexes for verification
        await list_existing_indexes(db)

    except Exception as e:
        logger.error(f"❌ Error setting up indexes: {e}")
        sys.exit(1)

    finally:
        client.close()
        logger.info("\n✓ MongoDB connection closed")


def main() -> None:
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("MongoDB Index Setup for Nutrifit Backend")
    logger.info("=" * 60 + "\n")

    try:
        asyncio.run(setup_all_indexes())
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
