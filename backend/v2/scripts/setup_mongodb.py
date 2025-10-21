#!/usr/bin/env python3
"""
MongoDB initialization script for V2.

Creates collections and indexes for the refactored meal system.

Usage:
    python backend/v2/scripts/setup_mongodb.py
"""

import asyncio
import sys
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import CollectionInvalid
import structlog

logger = structlog.get_logger(__name__)


async def create_collections(db: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
    """Create MongoDB collections."""
    collections_to_create = [
        "meals",
        "meal_analysis",
        "activity_events",
        "health_totals",
    ]

    for collection_name in collections_to_create:
        try:
            await db.create_collection(collection_name)
            logger.info(f"✅ Created collection: {collection_name}")
        except CollectionInvalid:
            logger.info(f"ℹ️  Collection already exists: {collection_name}")


async def create_indexes(db: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
    """Create MongoDB indexes for optimal query performance."""

    # ═══════════════════════════════════════════════════════════
    # MEALS COLLECTION INDEXES
    # ═══════════════════════════════════════════════════════════
    meals = db.meals

    # Query by user + timestamp (most common query)
    await meals.create_index(
        [("user_id", 1), ("timestamp", -1)],
        name="idx_user_timestamp",
    )
    logger.info("✅ Created index: meals.idx_user_timestamp")

    # Query by user + created_at (audit queries)
    await meals.create_index(
        [("user_id", 1), ("created_at", -1)],
        name="idx_user_created_at",
    )
    logger.info("✅ Created index: meals.idx_user_created_at")

    # Idempotency key (unique constraint)
    await meals.create_index(
        "idempotency_key", unique=True, sparse=True, name="idx_idempotency_key"
    )
    logger.info("✅ Created index: meals.idx_idempotency_key (unique)")

    # Analysis ID (link to temporary analysis)
    await meals.create_index("analysis_id", sparse=True, name="idx_analysis_id")
    logger.info("✅ Created index: meals.idx_analysis_id")

    # Barcode (for barcode-based meals)
    await meals.create_index("barcode", sparse=True, name="idx_barcode")
    logger.info("✅ Created index: meals.idx_barcode")

    # Source (filter by input method)
    await meals.create_index("source", name="idx_source")
    logger.info("✅ Created index: meals.idx_source")

    # ═══════════════════════════════════════════════════════════
    # MEAL_ANALYSIS COLLECTION INDEXES (Temporary Storage)
    # ═══════════════════════════════════════════════════════════
    meal_analysis = db.meal_analysis

    # TTL index (auto-delete after 24 hours)
    await meal_analysis.create_index(
        "expires_at",
        expireAfterSeconds=0,
        name="idx_ttl_expires_at",
    )
    logger.info("✅ Created TTL index: meal_analysis.idx_ttl_expires_at")

    # Query by user (list user's pending analyses)
    await meal_analysis.create_index(
        [("user_id", 1), ("created_at", -1)], name="idx_user_created_at"
    )
    logger.info("✅ Created index: meal_analysis.idx_user_created_at")

    # Idempotency key (unique constraint)
    await meal_analysis.create_index(
        "idempotency_key", unique=True, sparse=True, name="idx_idempotency_key"
    )
    logger.info("✅ Created index: meal_analysis.idx_idempotency_key (unique)")

    # Status (query pending/completed)
    await meal_analysis.create_index("status", name="idx_status")
    logger.info("✅ Created index: meal_analysis.idx_status")

    # ═══════════════════════════════════════════════════════════
    # ACTIVITY_EVENTS COLLECTION (V1 - Keep Unchanged)
    # ═══════════════════════════════════════════════════════════
    # Note: Activity events are V1 domain, not modified in V2
    logger.info("ℹ️  Skipping activity_events indexes (V1 domain)")

    # ═══════════════════════════════════════════════════════════
    # HEALTH_TOTALS COLLECTION (V1 - Keep Unchanged)
    # ═══════════════════════════════════════════════════════════
    # Note: Health totals are V1 domain, not modified in V2
    logger.info("ℹ️  Skipping health_totals indexes (V1 domain)")


async def verify_indexes(db: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
    """Verify all indexes were created successfully."""

    meals_indexes = await db.meals.index_information()
    analysis_indexes = await db.meal_analysis.index_information()

    expected_meals_indexes = [
        "idx_user_timestamp",
        "idx_user_created_at",
        "idx_idempotency_key",
        "idx_analysis_id",
        "idx_barcode",
        "idx_source",
    ]

    expected_analysis_indexes = [
        "idx_ttl_expires_at",
        "idx_user_created_at",
        "idx_idempotency_key",
        "idx_status",
    ]

    logger.info("\n📊 Index Verification:")
    logger.info(f"Meals indexes: {len(meals_indexes)} total")
    for idx_name in expected_meals_indexes:
        if idx_name in meals_indexes:
            logger.info(f"  ✅ {idx_name}")
        else:
            logger.error(f"  ❌ {idx_name} MISSING")

    logger.info(f"\nMeal Analysis indexes: {len(analysis_indexes)} total")
    for idx_name in expected_analysis_indexes:
        if idx_name in analysis_indexes:
            logger.info(f"  ✅ {idx_name}")
        else:
            logger.error(f"  ❌ {idx_name} MISSING")


async def main() -> int:
    """Main setup function."""

    # Default MongoDB connection (override with env var if needed)
    mongodb_uri = "mongodb://localhost:27017"
    database_name = "nutrifit"

    logger.info("🔧 MongoDB V2 Setup Starting...")
    logger.info(f"URI: {mongodb_uri}")
    logger.info(f"Database: {database_name}")

    try:
        # Connect to MongoDB
        client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(mongodb_uri)
        db = client[database_name]

        # Test connection
        await client.admin.command("ping")
        logger.info("✅ MongoDB connection successful")

        # Create collections
        logger.info("\n📦 Creating collections...")
        await create_collections(db)

        # Create indexes
        logger.info("\n🔍 Creating indexes...")
        await create_indexes(db)

        # Verify
        logger.info("\n✨ Verifying setup...")
        await verify_indexes(db)

        logger.info("\n🎉 MongoDB V2 setup completed successfully!")

        # Close connection
        client.close()

        return 0

    except Exception as e:
        logger.error(f"\n❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
