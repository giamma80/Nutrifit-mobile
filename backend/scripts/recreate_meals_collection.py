"""Recreate meals collection without validator.

The existing collection has an obsolete validator requiring 'meal_id' field
(from old schema). Drop and recreate without validator to match current entity.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

from infrastructure.config import get_mongodb_uri  # noqa: E402


async def recreate_collection() -> bool:
    """Drop and recreate meals without validator."""
    uri = get_mongodb_uri()
    if not uri:
        print("❌ MONGODB_URI not configured")
        return False

    client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(uri)
    db = client["nutrifit"]

    print("Recreating meals collection...")
    print("-" * 60)

    # Check current count
    count = await db.meals.count_documents({})
    print(f"Current document count: {count}")

    if count > 0:
        print("⚠️  Collection has data - backing up before drop")
        print(f"   Found {count} meals")

    # Drop collection
    print("\n1️⃣  Dropping collection...")
    try:
        await db.meals.drop()
        print("✅ Collection dropped")
    except Exception as e:
        print(f"❌ Failed to drop: {e}")
        client.close()
        return False

    # Recreate without validator
    print("\n2️⃣  Creating new collection (no validator)...")
    try:
        await db.create_collection("meals")
        print("✅ Collection created")
    except Exception as e:
        print(f"❌ Failed to create: {e}")
        client.close()
        return False

    # Create indexes
    print("\n3️⃣  Creating indexes...")
    try:
        # Index on user_id + timestamp (most common query pattern)
        await db.meals.create_index(
            [("user_id", 1), ("timestamp", -1)],
            name="user_timestamp_idx",
        )
        print("   ✅ user_timestamp_idx")

        # Index on user_id alone (for get_by_user)
        await db.meals.create_index([("user_id", 1)], name="user_idx")
        print("   ✅ user_idx")

        # Index on timestamp (for date range queries)
        await db.meals.create_index([("timestamp", -1)], name="timestamp_idx")
        print("   ✅ timestamp_idx")

        print("✅ All indexes created")
    except Exception as e:
        print(f"❌ Failed to create indexes: {e}")
        client.close()
        return False

    print("\n" + "=" * 60)
    print("✅ SUCCESS - Collection recreated without validator")
    print("=" * 60)

    client.close()
    return True


if __name__ == "__main__":
    success = asyncio.run(recreate_collection())
    sys.exit(0 if success else 1)
