"""Unit tests for InMemoryProfileRepository.

Tests focus on:
- Repository initialization
- Save and retrieve operations
- Query methods (find_by_id, find_by_user_id)
- Delete operations
- Existence checks
- Edge cases and immutability

Note: These are UNIT tests for in-memory implementation.
"""

import pytest

from infrastructure.persistence.in_memory.profile_repository import (
    InMemoryProfileRepository,
)
from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId
from domain.nutritional_profile.core.value_objects.user_data import UserData
from domain.nutritional_profile.core.value_objects.bmr import BMR
from domain.nutritional_profile.core.value_objects.tdee import TDEE
from domain.nutritional_profile.core.value_objects.macro_split import MacroSplit  # noqa: E501
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.activity_level import (
    ActivityLevel,
)


@pytest.fixture
def repository() -> InMemoryProfileRepository:
    """Fixture providing clean InMemoryProfileRepository."""
    return InMemoryProfileRepository()


@pytest.fixture
def sample_profile() -> NutritionalProfile:
    """Fixture providing sample nutritional profile."""
    user_data = UserData(
        weight=70.0,
        height=175.0,
        age=30,
        sex="M",
        activity_level=ActivityLevel.MODERATE,
    )
    goal = Goal.CUT
    bmr = BMR(value=1680.0)
    tdee = TDEE(value=2604.0)
    macro_split = MacroSplit(
        protein_g=156,
        carbs_g=208,
        fat_g=69,
    )

    profile = NutritionalProfile(
        profile_id=ProfileId.generate(),
        user_id="user123",
        user_data=user_data,
        goal=goal,
        bmr=bmr,
        tdee=tdee,
        calories_target=2080.0,
        macro_split=macro_split,
    )
    return profile


class TestRepositoryInit:
    """Test repository initialization."""

    def test_init(self) -> None:
        """Test repository initializes with empty storage."""
        repository = InMemoryProfileRepository()
        assert repository._profiles == {}
        assert repository.count() == 0


class TestSave:
    """Test save method."""

    @pytest.mark.asyncio
    async def test_save_new_profile(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test saving a new profile."""
        await repository.save(sample_profile)

        # Verify profile is in storage
        assert str(sample_profile.profile_id) in repository._profiles
        stored = repository._profiles[str(sample_profile.profile_id)]
        assert stored.user_id == "user123"
        assert stored.goal == Goal.CUT
        assert repository.count() == 1

    @pytest.mark.asyncio
    async def test_save_updates_existing_profile(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test saving updates an existing profile."""
        await repository.save(sample_profile)

        # Modify profile
        original_id = sample_profile.profile_id
        sample_profile.calories_target = 2200.0

        # Save again
        await repository.save(sample_profile)

        # Verify only one profile exists
        assert repository.count() == 1
        stored = repository._profiles[str(original_id)]
        assert stored.calories_target == 2200.0

    @pytest.mark.asyncio
    async def test_save_creates_deep_copy(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test that save creates deep copy to prevent external mutations."""
        await repository.save(sample_profile)

        # Modify original profile
        sample_profile.calories_target = 9999.0

        # Verify stored profile unchanged
        stored = repository._profiles[str(sample_profile.profile_id)]
        assert stored.calories_target != 9999.0
        assert stored.calories_target == 2080.0


class TestFindById:
    """Test find_by_id method."""

    @pytest.mark.asyncio
    async def test_find_by_id_success(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test finding profile by ID."""
        await repository.save(sample_profile)

        found = await repository.find_by_id(sample_profile.profile_id)

        assert found is not None
        assert found.profile_id == sample_profile.profile_id
        assert found.user_id == sample_profile.user_id
        assert found.goal == sample_profile.goal

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(
        self, repository: InMemoryProfileRepository
    ) -> None:  # noqa: E501
        """Test finding non-existent profile returns None."""
        random_id = ProfileId.generate()
        found = await repository.find_by_id(random_id)

        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_id_returns_deep_copy(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test that find_by_id returns deep copy."""
        await repository.save(sample_profile)

        found = await repository.find_by_id(sample_profile.profile_id)
        assert found is not None

        # Modify returned profile
        found.calories_target = 9999.0

        # Verify stored profile unchanged
        stored = repository._profiles[str(sample_profile.profile_id)]
        assert stored.calories_target == 2080.0


class TestFindByUserId:
    """Test find_by_user_id method."""

    @pytest.mark.asyncio
    async def test_find_by_user_id_success(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test finding profile by user ID."""
        await repository.save(sample_profile)

        found = await repository.find_by_user_id("user123")

        assert found is not None
        assert found.user_id == "user123"
        assert found.profile_id == sample_profile.profile_id

    @pytest.mark.asyncio
    async def test_find_by_user_id_not_found(
        self, repository: InMemoryProfileRepository
    ) -> None:  # noqa: E501
        """Test finding non-existent user returns None."""
        found = await repository.find_by_user_id("nonexistent")

        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_user_id_returns_deep_copy(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test that find_by_user_id returns deep copy."""
        await repository.save(sample_profile)

        found = await repository.find_by_user_id("user123")
        assert found is not None

        # Modify returned profile
        found.calories_target = 9999.0

        # Verify stored profile unchanged
        stored = repository._profiles[str(sample_profile.profile_id)]
        assert stored.calories_target == 2080.0

    @pytest.mark.asyncio
    async def test_find_by_user_id_multiple_profiles(
        self, repository: InMemoryProfileRepository
    ) -> None:
        """Test find_by_user_id returns first match (edge case)."""
        # Create two profiles for different users
        profile1 = NutritionalProfile(
            profile_id=ProfileId.generate(),
            user_id="user1",
            user_data=UserData(70.0, 175.0, 30, "M", ActivityLevel.SEDENTARY),
            goal=Goal.CUT,
            bmr=BMR(1680.0),
            tdee=TDEE(2016.0),
            calories_target=1800.0,
            macro_split=MacroSplit(135, 180, 60),
        )
        profile2 = NutritionalProfile(
            profile_id=ProfileId.generate(),
            user_id="user2",
            user_data=UserData(60.0, 165.0, 25, "F", ActivityLevel.SEDENTARY),
            goal=Goal.BULK,
            bmr=BMR(1400.0),
            tdee=TDEE(1680.0),
            calories_target=1900.0,
            macro_split=MacroSplit(119, 238, 53),
        )

        await repository.save(profile1)
        await repository.save(profile2)

        # Find each user
        found1 = await repository.find_by_user_id("user1")
        found2 = await repository.find_by_user_id("user2")

        assert found1 is not None
        assert found1.user_id == "user1"
        assert found2 is not None
        assert found2.user_id == "user2"


class TestDelete:
    """Test delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test deleting a profile."""
        await repository.save(sample_profile)
        assert repository.count() == 1

        await repository.delete(sample_profile.profile_id)

        assert repository.count() == 0
        assert str(sample_profile.profile_id) not in repository._profiles

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, repository: InMemoryProfileRepository
    ) -> None:  # noqa: E501
        """Test deleting non-existent profile (no error)."""
        random_id = ProfileId.generate()

        # Should not raise error
        await repository.delete(random_id)

        assert repository.count() == 0


class TestExists:
    """Test exists method."""

    @pytest.mark.asyncio
    async def test_exists_true(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test exists returns True for existing user."""
        await repository.save(sample_profile)

        result = await repository.exists("user123")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repository: InMemoryProfileRepository) -> None:  # noqa: E501
        """Test exists returns False for non-existent user."""
        result = await repository.exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_after_delete(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test exists returns False after deletion."""
        await repository.save(sample_profile)
        assert await repository.exists("user123") is True

        await repository.delete(sample_profile.profile_id)

        assert await repository.exists("user123") is False


class TestUtilityMethods:
    """Test utility methods (clear, count)."""

    def test_count_empty(self, repository: InMemoryProfileRepository) -> None:
        """Test count on empty repository."""
        assert repository.count() == 0

    @pytest.mark.asyncio
    async def test_count_single(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test count with single profile."""
        await repository.save(sample_profile)

        assert repository.count() == 1

    @pytest.mark.asyncio
    async def test_count_multiple(
        self, repository: InMemoryProfileRepository
    ) -> None:  # noqa: E501
        """Test count with multiple profiles."""
        profile1 = NutritionalProfile(
            profile_id=ProfileId.generate(),
            user_id="user1",
            user_data=UserData(70.0, 175.0, 30, "M", ActivityLevel.SEDENTARY),
            goal=Goal.CUT,
            bmr=BMR(1680.0),
            tdee=TDEE(2016.0),
            calories_target=1800.0,
            macro_split=MacroSplit(135, 180, 60),
        )
        profile2 = NutritionalProfile(
            profile_id=ProfileId.generate(),
            user_id="user2",
            user_data=UserData(60.0, 165.0, 25, "F", ActivityLevel.SEDENTARY),
            goal=Goal.BULK,
            bmr=BMR(1400.0),
            tdee=TDEE(1680.0),
            calories_target=1900.0,
            macro_split=MacroSplit(119, 238, 53),
        )

        await repository.save(profile1)
        await repository.save(profile2)

        assert repository.count() == 2

    @pytest.mark.asyncio
    async def test_clear(
        self,
        repository: InMemoryProfileRepository,
        sample_profile: NutritionalProfile,  # noqa: E501
    ) -> None:
        """Test clear removes all profiles."""
        await repository.save(sample_profile)
        assert repository.count() == 1

        repository.clear()

        assert repository.count() == 0
        assert repository._profiles == {}

    @pytest.mark.asyncio
    async def test_clear_empty_repository(
        self, repository: InMemoryProfileRepository
    ) -> None:  # noqa: E501
        """Test clear on empty repository (no error)."""
        repository.clear()

        assert repository.count() == 0
