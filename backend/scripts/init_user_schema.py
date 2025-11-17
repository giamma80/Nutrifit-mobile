"""MongoDB schema initialization and indexes for User domain.

This script creates the necessary indexes for optimal query performance
and ensures data integrity constraints.

Run with: python -m scripts.init_user_schema
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


async def create_user_indexes() -> None:
    """Create MongoDB indexes for users collection.

    Indexes:
    - auth0_sub: Unique index (primary key)
    - user_id: Unique index (internal UUID)
    - is_active: Index for filtering active users
    - created_at: Index for sorting/filtering
    - last_authenticated_at: Index for activity queries
    """
    # Connect to MongoDB
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DATABASE", "nutrifit")

    client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_url)  # type: ignore
    db = client[db_name]
    users_collection = db.users

    print(f"Creating indexes for {db_name}.users collection...")

    # 1. Unique index on auth0_sub (primary lookup key)
    await users_collection.create_index(
        "auth0_sub",
        unique=True,
        name="idx_auth0_sub_unique",
    )
    print("✓ Created unique index on auth0_sub")

    # 2. Unique index on user_id (secondary lookup key)
    await users_collection.create_index(
        "user_id",
        unique=True,
        name="idx_user_id_unique",
    )
    print("✓ Created unique index on user_id")

    # 3. Index on is_active (for filtering)
    await users_collection.create_index(
        "is_active",
        name="idx_is_active",
    )
    print("✓ Created index on is_active")

    # 4. Index on created_at (for sorting)
    await users_collection.create_index(
        "created_at",
        name="idx_created_at",
    )
    print("✓ Created index on created_at")

    # 5. Index on last_authenticated_at (for activity tracking)
    await users_collection.create_index(
        "last_authenticated_at",
        name="idx_last_authenticated_at",
    )
    print("✓ Created index on last_authenticated_at")

    # 6. Compound index for active user queries with recent activity
    await users_collection.create_index(
        [("is_active", 1), ("last_authenticated_at", -1)],
        name="idx_active_recent",
    )
    print("✓ Created compound index on is_active + last_authenticated_at")

    # List all indexes
    indexes = await users_collection.list_indexes().to_list(length=100)
    print("\nAll indexes on users collection:")
    for idx in indexes:
        print(f"  - {idx['name']}: {idx.get('key', {})}")

    # Close connection
    client.close()
    print("\n✓ Index creation completed successfully")


async def verify_schema() -> None:
    """Verify that the schema and indexes are correctly set up."""
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DATABASE", "nutrifit")

    client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_url)  # type: ignore
    db = client[db_name]
    users_collection = db.users

    print("\nVerifying schema...")

    # Check indexes
    indexes = await users_collection.list_indexes().to_list(length=100)
    index_names = {idx["name"] for idx in indexes}

    required_indexes = {
        "idx_auth0_sub_unique",
        "idx_user_id_unique",
        "idx_is_active",
        "idx_created_at",
        "idx_last_authenticated_at",
        "idx_active_recent",
    }

    missing = required_indexes - index_names
    if missing:
        print(f"⚠ Missing indexes: {missing}")
    else:
        print("✓ All required indexes present")

    # Check collection stats
    stats = await db.command("collStats", "users")
    print("\nCollection stats:")
    print(f"  - Documents: {stats.get('count', 0)}")
    print(f"  - Size: {stats.get('size', 0)} bytes")
    print(f"  - Indexes: {stats.get('nindexes', 0)}")

    client.close()


if __name__ == "__main__":
    print("=== User Domain MongoDB Schema Initialization ===\n")
    asyncio.run(create_user_indexes())
    asyncio.run(verify_schema())
