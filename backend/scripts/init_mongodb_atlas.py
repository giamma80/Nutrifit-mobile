#!/usr/bin/env python3
"""Initialize MongoDB Atlas with schema validation and indexes.

This script creates collections with schema validation and indexes
matching the local Docker MongoDB setup (init-mongo.js).

Usage:
    uv run python scripts/init_mongodb_atlas.py

Environment:
    MONGODB_URI: MongoDB Atlas connection string (required)
"""

import asyncio
import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


async def init_mongodb_atlas() -> None:
    """Initialize MongoDB Atlas with collections, validation, and indexes."""

    # Get MongoDB URI from environment
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("❌ Error: MONGODB_URI environment variable not set")
        print("   Set it in .env or export it:")
        print('   export MONGODB_URI="mongodb+srv://..."')
        sys.exit(1)

    if "localhost" in mongodb_uri:
        print(
            "⚠️  Warning: Using localhost URI. Are you sure you want to run this on local MongoDB?"
        )
        response = input("Continue? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    print("🔗 Connecting to MongoDB...")
    print(f"   URI: {mongodb_uri.split('@')[1] if '@' in mongodb_uri else 'localhost'}")

    try:
        client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(
            mongodb_uri, serverSelectionTimeoutMS=10000
        )
        await client.admin.command("ping")
        print("✅ Connected successfully!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    db = client.nutrifit

    # ========================================
    # 1. MEALS COLLECTION
    # ========================================
    print("\n📊 Setting up 'meals' collection...")

    # Check if collection exists
    collections = await db.list_collection_names()
    if "meals" in collections:
        print("   Collection 'meals' already exists. Skipping creation.")
    else:
        # Create collection with schema validation
        await db.create_collection(
            "meals",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "meal_id", "timestamp"],
                    "properties": {
                        "user_id": {"bsonType": "string", "description": "User ID (required)"},
                        "meal_id": {
                            "bsonType": "string",
                            "description": "Unique meal ID (required)",
                        },
                        "timestamp": {
                            "bsonType": "date",
                            "description": "Meal timestamp (required)",
                        },
                    },
                }
            },
        )
        print("   ✅ Collection 'meals' created with schema validation")

    # Create indexes
    print("   Creating indexes...")
    await db.meals.create_index([("user_id", 1), ("timestamp", -1)])
    print("      ✅ Index on (user_id, timestamp)")

    await db.meals.create_index("meal_id", unique=True)
    print("      ✅ Unique index on meal_id")

    # ========================================
    # 2. NUTRITIONAL_PROFILES COLLECTION
    # ========================================
    print("\n📊 Setting up 'nutritional_profiles' collection...")

    if "nutritional_profiles" in collections:
        print("   Collection 'nutritional_profiles' already exists. Skipping creation.")
    else:
        await db.create_collection(
            "nutritional_profiles",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["profile_id", "user_id"],
                    "properties": {
                        "profile_id": {
                            "bsonType": "string",
                            "description": "Unique profile ID (required)",
                        },
                        "user_id": {"bsonType": "string", "description": "User ID (required)"},
                    },
                }
            },
        )
        print("   ✅ Collection 'nutritional_profiles' created with schema validation")

    # Create indexes
    print("   Creating indexes...")
    await db.nutritional_profiles.create_index("profile_id", unique=True)
    print("      ✅ Unique index on profile_id")

    await db.nutritional_profiles.create_index("user_id", unique=True)
    print("      ✅ Unique index on user_id")

    # ========================================
    # 3. ACTIVITY_EVENTS COLLECTION
    # ========================================
    print("\n📊 Setting up 'activity_events' collection...")

    if "activity_events" in collections:
        print("   Collection 'activity_events' already exists. Skipping creation.")
    else:
        await db.create_collection(
            "activity_events",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "timestamp"],
                    "properties": {
                        "user_id": {"bsonType": "string", "description": "User ID (required)"},
                        "timestamp": {
                            "bsonType": "date",
                            "description": "Event timestamp (required)",
                        },
                    },
                }
            },
        )
        print("   ✅ Collection 'activity_events' created with schema validation")

    # Create indexes
    print("   Creating indexes...")
    await db.activity_events.create_index([("user_id", 1), ("timestamp", -1)])
    print("      ✅ Index on (user_id, timestamp)")

    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "=" * 50)
    print("✅ MongoDB Atlas initialization complete!")
    print("=" * 50)

    # List all collections with document counts
    print("\n📋 Database summary:")
    collections = await db.list_collection_names()
    for coll_name in collections:
        count = await db[coll_name].count_documents({})
        print(f"   - {coll_name}: {count} documents")

    client.close()
    print("\n✅ Connection closed.")


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    print("=" * 50)
    print("MongoDB Atlas Initialization Script")
    print("=" * 50)
    asyncio.run(init_mongodb_atlas())
