"""Unit tests for User entity."""

import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time

from domain.user.core.entities.user import User
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
from domain.user.core.events.user_created import UserCreated
from domain.user.core.events.user_authenticated import UserAuthenticated
from domain.user.core.events.user_updated import UserProfileUpdated


class TestUserEntity:
    """Test User entity."""

    @freeze_time("2025-01-01 12:00:00")
    def test_create_user_with_defaults(self):
        """Test creating user with default preferences."""
        auth0_sub = Auth0Sub("auth0|123456789")
        user = User.create(auth0_sub)

        assert user.auth0_sub == auth0_sub
        assert user.is_active is True
        assert user.preferences.data == {}
        assert user.last_authenticated_at is None
        assert user.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert user.updated_at == datetime(2025, 1, 1, 12, 0, 0)

    @freeze_time("2025-01-01 12:00:00")
    def test_create_user_with_preferences(self):
        """Test creating user with custom preferences."""
        auth0_sub = Auth0Sub("auth0|123456789")
        prefs = UserPreferences(data={"theme": "dark", "language": "it"})
        user = User.create(auth0_sub, prefs)

        assert user.preferences == prefs
        assert user.preferences.get("theme") == "dark"

    @freeze_time("2025-01-01 12:00:00")
    def test_create_emits_user_created_event(self):
        """Test that create() emits UserCreated event."""
        auth0_sub = Auth0Sub("auth0|123456789")
        user = User.create(auth0_sub)

        events = user.collect_events()
        assert len(events) == 1

        event = events[0]
        assert isinstance(event, UserCreated)
        assert event.user_id == user.user_id
        assert event.auth0_sub == auth0_sub
        assert event.created_at == datetime(2025, 1, 1, 12, 0, 0)

    def test_create_generates_unique_user_ids(self):
        """Test that each user gets unique user_id."""
        auth0_sub1 = Auth0Sub("auth0|123456789")
        auth0_sub2 = Auth0Sub("auth0|987654321")

        user1 = User.create(auth0_sub1)
        user2 = User.create(auth0_sub2)

        assert user1.user_id != user2.user_id

    @freeze_time("2025-01-01 12:00:00")
    def test_authenticate_updates_timestamp(self):
        """Test that authenticate() updates last_authenticated_at."""
        user = User.create(Auth0Sub("auth0|123456789"))
        user.collect_events()  # Clear creation events

        with freeze_time("2025-01-01 14:00:00"):
            user.authenticate()

        assert user.last_authenticated_at == datetime(2025, 1, 1, 14, 0, 0)
        assert user.updated_at == datetime(2025, 1, 1, 14, 0, 0)

    @freeze_time("2025-01-01 12:00:00")
    def test_authenticate_emits_event(self):
        """Test that authenticate() emits UserAuthenticated event."""
        user = User.create(Auth0Sub("auth0|123456789"))
        user.collect_events()  # Clear creation events

        with freeze_time("2025-01-01 14:00:00"):
            user.authenticate()

        events = user.collect_events()
        assert len(events) == 1

        event = events[0]
        assert isinstance(event, UserAuthenticated)
        assert event.user_id == user.user_id
        assert event.authenticated_at == datetime(2025, 1, 1, 14, 0, 0)

    @freeze_time("2025-01-01 12:00:00")
    def test_authenticate_with_custom_timestamp(self):
        """Test authenticate() with custom timestamp."""
        user = User.create(Auth0Sub("auth0|123456789"))
        custom_time = datetime(2025, 1, 1, 15, 0, 0)

        user.authenticate(authenticated_at=custom_time)

        assert user.last_authenticated_at == custom_time

    @freeze_time("2025-01-01 12:00:00")
    def test_authenticate_before_creation_raises_error(self):
        """Test that authenticating before creation raises error."""
        user = User.create(Auth0Sub("auth0|123456789"))
        past_time = datetime(2024, 12, 31, 12, 0, 0)

        with pytest.raises(ValueError, match="cannot be before user creation time"):
            user.authenticate(authenticated_at=past_time)

    @freeze_time("2025-01-01 12:00:00")
    def test_update_preferences(self):
        """Test updating user preferences."""
        user = User.create(Auth0Sub("auth0|123456789"))
        user.collect_events()  # Clear creation events

        new_prefs = UserPreferences(data={"theme": "dark"})
        with freeze_time("2025-01-01 14:00:00"):
            user.update_preferences(new_prefs)

        assert user.preferences == new_prefs
        assert user.updated_at == datetime(2025, 1, 1, 14, 0, 0)

    @freeze_time("2025-01-01 12:00:00")
    def test_update_preferences_emits_event(self):
        """Test that update_preferences() emits UserProfileUpdated event."""
        old_prefs = UserPreferences(data={"theme": "light"})
        user = User.create(Auth0Sub("auth0|123456789"), old_prefs)
        user.collect_events()  # Clear creation events

        new_prefs = UserPreferences(data={"theme": "dark"})
        with freeze_time("2025-01-01 14:00:00"):
            user.update_preferences(new_prefs)

        events = user.collect_events()
        assert len(events) == 1

        event = events[0]
        assert isinstance(event, UserProfileUpdated)
        assert event.old_preferences == old_prefs
        assert event.new_preferences == new_prefs
        assert event.updated_at == datetime(2025, 1, 1, 14, 0, 0)

    @freeze_time("2025-01-01 12:00:00")
    def test_deactivate_user(self):
        """Test deactivating user account."""
        user = User.create(Auth0Sub("auth0|123456789"))

        with freeze_time("2025-01-01 14:00:00"):
            user.deactivate()

        assert user.is_active is False
        assert user.updated_at == datetime(2025, 1, 1, 14, 0, 0)

    def test_deactivate_already_inactive_user(self):
        """Test that deactivating already inactive user is idempotent."""
        user = User.create(Auth0Sub("auth0|123456789"))
        user.deactivate()

        first_updated = user.updated_at
        user.deactivate()

        assert user.is_active is False
        assert user.updated_at == first_updated  # No change

    @freeze_time("2025-01-01 12:00:00")
    def test_reactivate_user(self):
        """Test reactivating user account."""
        user = User.create(Auth0Sub("auth0|123456789"))
        user.deactivate()

        with freeze_time("2025-01-01 14:00:00"):
            user.reactivate()

        assert user.is_active is True
        assert user.updated_at == datetime(2025, 1, 1, 14, 0, 0)

    def test_reactivate_already_active_user(self):
        """Test that reactivating already active user is idempotent."""
        user = User.create(Auth0Sub("auth0|123456789"))

        first_updated = user.updated_at
        user.reactivate()

        assert user.is_active is True
        assert user.updated_at == first_updated  # No change

    def test_collect_events_returns_and_clears(self):
        """Test that collect_events() returns events and clears them."""
        user = User.create(Auth0Sub("auth0|123456789"))

        events1 = user.collect_events()
        assert len(events1) == 1

        events2 = user.collect_events()
        assert len(events2) == 0  # Cleared after first collection

    def test_multiple_operations_accumulate_events(self):
        """Test that multiple operations accumulate events."""
        user = User.create(Auth0Sub("auth0|123456789"))
        user.authenticate()
        user.update_preferences(UserPreferences(data={"theme": "dark"}))

        events = user.collect_events()
        assert len(events) == 3
        assert isinstance(events[0], UserCreated)
        assert isinstance(events[1], UserAuthenticated)
        assert isinstance(events[2], UserProfileUpdated)

    def test_user_equality_based_on_user_id(self):
        """Test that user equality is based on user_id."""
        auth0_sub = Auth0Sub("auth0|123456789")
        user1 = User.create(auth0_sub)

        # Create another user instance with same user_id (simulating load from DB)
        user2 = User(
            user_id=user1.user_id,
            auth0_sub=auth0_sub,
            preferences=UserPreferences.default(),
            created_at=user1.created_at,
            updated_at=user1.updated_at,
        )

        assert user1 == user2

    def test_user_inequality(self):
        """Test that users with different user_ids are not equal."""
        user1 = User.create(Auth0Sub("auth0|123456789"))
        user2 = User.create(Auth0Sub("auth0|987654321"))

        assert user1 != user2

    def test_user_hash_based_on_user_id(self):
        """Test that user hash is based on user_id."""
        user = User.create(Auth0Sub("auth0|123456789"))

        user_set = {user}
        assert user in user_set

        user_dict = {user: "data"}
        assert user in user_dict

        # Verify hash is consistent
        hash1 = hash(user)
        hash2 = hash(user)
        assert hash1 == hash2

    def test_created_at_in_future_raises_error(self):
        """Test that created_at in future raises ValueError."""
        future_time = datetime.utcnow() + timedelta(hours=1)

        with pytest.raises(ValueError, match="cannot be in the future"):
            User(
                user_id=UserId.generate(),
                auth0_sub=Auth0Sub("auth0|123456789"),
                preferences=UserPreferences.default(),
                created_at=future_time,
                updated_at=future_time,
            )

    @freeze_time("2025-01-01 12:00:00")
    def test_last_authenticated_before_created_raises_error(self):
        """Test that last_authenticated_at before created_at raises error."""
        created = datetime(2025, 1, 1, 12, 0, 0)
        authenticated = datetime(2025, 1, 1, 10, 0, 0)  # Before creation

        with pytest.raises(ValueError, match="cannot be before created_at"):
            User(
                user_id=UserId.generate(),
                auth0_sub=Auth0Sub("auth0|123456789"),
                preferences=UserPreferences.default(),
                created_at=created,
                updated_at=created,
                last_authenticated_at=authenticated,
            )

    def test_user_with_different_auth0_providers(self):
        """Test users with different Auth0 providers."""
        user1 = User.create(Auth0Sub("auth0|123456789"))
        user2 = User.create(Auth0Sub("google-oauth2|987654321"))
        user3 = User.create(Auth0Sub("facebook|111222333"))

        assert user1.auth0_sub.provider == "auth0"
        assert user2.auth0_sub.provider == "google-oauth2"
        assert user3.auth0_sub.provider == "facebook"
        assert user1 != user2 != user3
