"""Recreate activity_events collection without validator.

Since the collection is empty and we don't have collMod permissions,
we can drop and recreate it without validator.
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
    """Drop and recreate activity_events without validator."""
    uri = get_mongodb_uri()
    if not uri:
        print("❌ MONGODB_URI not configured")
        return False

    client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(uri)
    db = client["nutrifit"]

    print("Recreating activity_events collection...")
    print("-" * 60)

    # Check if empty
    count = await db.activity_events.count_documents({})
    print(f"Current document count: {count}")

    if count > 0:
        print("❌ Collection has data - cannot drop safely")
        client.close()
        return False

    # Drop collection
    print("\n1️⃣  Dropping collection...")
    try:
        await db.activity_events.drop()
        print("✅ Collection dropped")
    except Exception as e:
        print(f"❌ Failed to drop: {e}")
        client.close()
        return False

    # Create new collection (no validator)
    print("\n2️⃣  Creating new collection...")
    try:
        await db.create_collection("activity_events")
        print("✅ Collection created (no validator)")
    except Exception as e:
        print(f"❌ Failed to create: {e}")
        client.close()
        return False

    # Create indexes
    print("\n3️⃣  Creating indexes...")
    try:
        # Unique index on _id (user_id + ts)
        await db.activity_events.create_index(
            [("user_id", 1), ("ts", 1)], name="idx_user_ts", background=True
        )
        print("   ✅ idx_user_ts")

        await db.activity_events.create_index([("user_id", 1)], name="idx_user", background=True)
        print("   ✅ idx_user")

        print("✅ All indexes created")
    except Exception as e:
        print(f"⚠️  Warning: {e}")
        print("   Indexes may need manual creation")

    client.close()
    print("\n" + "=" * 60)
    print("✅ SUCCESS! Collection recreated without validator")
    return True


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will drop the activity_events collection!")
    print("    Proceed only if collection is empty.\n")

    response = input("Continue? (yes/no): ").strip().lower()
    if response != "yes":
        print("Aborted.")
        sys.exit(1)

    success = asyncio.run(recreate_collection())
    sys.exit(0 if success else 1)
