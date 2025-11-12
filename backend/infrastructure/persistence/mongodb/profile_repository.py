"""MongoDB implementation of IProfileRepository."""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.entities.progress_record import (
    ProgressRecord,
)
from domain.nutritional_profile.core.ports.repository import IProfileRepository
from domain.nutritional_profile.core.value_objects.bmr import BMR
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.macro_split import (
    MacroSplit,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId
from domain.nutritional_profile.core.value_objects.activity_level import (
    ActivityLevel,
)
from domain.nutritional_profile.core.value_objects.tdee import TDEE
from domain.nutritional_profile.core.value_objects.user_data import UserData

from .base import MongoBaseRepository


class MongoProfileRepository(
    MongoBaseRepository[NutritionalProfile],
    IProfileRepository,
):
    """MongoDB implementation of nutritional profile repository."""

    @property
    def collection_name(self) -> str:
        """MongoDB collection name."""
        return "nutritional_profiles"

    def to_document(self, entity: NutritionalProfile) -> Dict[str, Any]:
        """Convert NutritionalProfile entity to MongoDB document.

        Args:
            entity: Domain entity

        Returns:
            dict: MongoDB document
        """
        profile = entity
        return {
            "_id": str(profile.profile_id.value),
            "profile_id": str(profile.profile_id.value),
            "user_id": profile.user_id,
            "user_data": {
                "weight": profile.user_data.weight,
                "height": profile.user_data.height,
                "age": profile.user_data.age,
                "sex": profile.user_data.sex,
                "activity_level": profile.user_data.activity_level.value,
            },
            "goal": profile.goal.value,
            "bmr": profile.bmr.value,
            "tdee": profile.tdee.value,
            "calories_target": profile.calories_target,
            "macro_split": {
                "protein_g": profile.macro_split.protein_g,
                "carbs_g": profile.macro_split.carbs_g,
                "fat_g": profile.macro_split.fat_g,
            },
            "progress_history": [
                {
                    "record_id": str(record.record_id),
                    "date": record.date.isoformat(),
                    "weight": record.weight,
                    "consumed_calories": record.consumed_calories,
                    "consumed_protein_g": record.consumed_protein_g,
                    "consumed_carbs_g": record.consumed_carbs_g,
                    "consumed_fat_g": record.consumed_fat_g,
                }
                for record in profile.progress_history
            ],
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
        }

    def from_document(self, doc: Dict[str, Any]) -> NutritionalProfile:
        """Convert MongoDB document to NutritionalProfile entity.

        Args:
            doc: MongoDB document

        Returns:
            NutritionalProfile: Domain entity
        """
        return NutritionalProfile(
            profile_id=ProfileId(doc["profile_id"]),
            user_id=doc["user_id"],
            user_data=UserData(
                weight=doc["user_data"]["weight"],
                height=doc["user_data"]["height"],
                age=doc["user_data"]["age"],
                sex=doc["user_data"]["sex"],
                activity_level=ActivityLevel(doc["user_data"]["activity_level"]),
            ),
            goal=Goal(doc["goal"]),
            bmr=BMR(doc["bmr"]),
            tdee=TDEE(doc["tdee"]),
            calories_target=doc["calories_target"],
            macro_split=MacroSplit(
                protein_g=doc["macro_split"]["protein_g"],
                carbs_g=doc["macro_split"]["carbs_g"],
                fat_g=doc["macro_split"]["fat_g"],
            ),
            progress_history=[
                ProgressRecord(
                    record_id=UUID(record["record_id"]),
                    profile_id=ProfileId(doc["profile_id"]),
                    date=datetime.fromisoformat(record["date"]).date(),
                    weight=record["weight"],
                    consumed_calories=record.get("consumed_calories"),
                    consumed_protein_g=record.get("consumed_protein_g"),
                    consumed_carbs_g=record.get("consumed_carbs_g"),
                    consumed_fat_g=record.get("consumed_fat_g"),
                )
                for record in doc.get("progress_history", [])
            ],
            created_at=datetime.fromisoformat(doc["created_at"]),
            updated_at=datetime.fromisoformat(doc["updated_at"]),
        )

    async def save(self, profile: NutritionalProfile) -> None:
        """Save profile (create or update)."""
        from datetime import timezone

        profile.updated_at = datetime.now(timezone.utc)

        document = self.to_document(profile)
        filter_dict = {"_id": document["_id"]}
        update_dict = {"$set": document}

        await self._update_one(filter_dict, update_dict, upsert=True)

    async def find_by_id(self, profile_id: ProfileId) -> NutritionalProfile | None:
        """Find profile by ID."""
        filter_dict = {"_id": str(profile_id.value)}

        doc = await self._find_one(filter_dict)
        if doc is None:
            return None

        return self.from_document(doc)

    async def find_by_user_id(self, user_id: str) -> NutritionalProfile | None:
        """Find profile by user ID."""
        filter_dict = {"user_id": user_id}

        doc = await self._find_one(filter_dict)
        if doc is None:
            return None

        return self.from_document(doc)

    async def delete(self, profile_id: ProfileId) -> None:
        """Delete profile (soft delete)."""
        filter_dict = {"_id": str(profile_id.value)}
        await self._delete_one(filter_dict)

    async def exists(self, user_id: str) -> bool:
        """Check if profile exists for user."""
        filter_dict = {"user_id": user_id}

        doc = await self._find_one(filter_dict, projection={"_id": 1})
        return doc is not None
