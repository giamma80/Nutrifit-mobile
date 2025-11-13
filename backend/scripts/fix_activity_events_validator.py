"""Fix MongoDB validator for activity_events collection.

The validator was expecting 'timestamp' (date) but repository uses
'ts' (string). This script updates the validator to match schema.
"""

import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from infrastructure.config import get_mongodb_uri

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_validator():
    """Update activity_events validator to match repository schema."""
    uri = get_mongodb_uri()
    if not uri:
        raise ValueError("MONGODB_URI not configured")

    client: AsyncIOMotorClient = AsyncIOMotorClient(uri)
    db = client["nutrifit"]

    # New validator: ts as string (not timestamp as date)
    new_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "ts"],
            "properties": {
                "user_id": {
                    "bsonType": "string",
                    "description": "User ID (required)",
                },
                "ts": {
                    "bsonType": "string",
                    "description": "ISO 8601 timestamp string (required)",
                },
                "steps": {
                    "bsonType": ["int", "null"],
                    "description": "Steps count (optional)",
                },
                "calories_out": {
                    "bsonType": ["double", "null"],
                    "description": "Calories burned (optional)",
                },
                "hr_avg": {
                    "bsonType": ["double", "null"],
                    "description": "Average heart rate (optional)",
                },
                "source": {
                    "enum": ["APPLE_HEALTH", "GOOGLE_FIT", "MANUAL"],
                    "description": "Data source (required)",
                },
            },
        }
    }

    try:
        # Update collection validation
        result = await db.command(
            {
                "collMod": "activity_events",
                "validator": new_validator,
                # Allow existing docs that don't match
                "validationLevel": "moderate",
            }
        )

        logger.info(f"✅ Updated activity_events validator: {result}")
        logger.info(
            "Validator now requires 'ts' (string) "
            "instead of 'timestamp' (date)"
        )
        logger.info("This matches the MongoActivityRepository schema")

    except Exception as e:
        logger.error(f"❌ Failed to update validator: {e}")
        raise

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(fix_validator())
