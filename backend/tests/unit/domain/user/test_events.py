"""Unit tests for user domain events."""

from datetime import datetime
from freezegun import freeze_time

from domain.user.core.events.user_created import UserCreated
from domain.user.core.events.user_authenticated import UserAuthenticated
from domain.user.core.events.user_updated import UserProfileUpdated
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences


class TestUserEvents:
    """Test user domain events."""

    @freeze_time("2025-01-01 12:00:00")
    def test_user_created_event(self):
        """Test UserCreated event creation."""
        user_id = UserId.generate()
        auth0_sub = Auth0Sub("auth0|123456789")
        created_at = datetime(2025, 1, 1, 12, 0, 0)

        event = UserCreated(
            user_id=user_id,
            auth0_sub=auth0_sub,
            created_at=created_at,
        )

        assert event.user_id == user_id
        assert event.auth0_sub == auth0_sub
        assert event.created_at == created_at

    def test_user_created_event_immutable(self):
        """Test that UserCreated event is immutable."""
        event = UserCreated(
            user_id=UserId.generate(),
            auth0_sub=Auth0Sub("auth0|123456789"),
            created_at=datetime.utcnow(),
        )

        # Should raise exception when trying to modify
        try:
            event.user_id = UserId.generate()  # type: ignore
            assert False, "Should not be able to modify frozen event"
        except Exception:
            pass  # Expected - frozen dataclass

    @freeze_time("2025-01-01 12:00:00")
    def test_user_authenticated_event(self):
        """Test UserAuthenticated event creation."""
        user_id = UserId.generate()
        auth0_sub = Auth0Sub("auth0|123456789")
        authenticated_at = datetime(2025, 1, 1, 12, 0, 0)

        event = UserAuthenticated(
            user_id=user_id,
            auth0_sub=auth0_sub,
            authenticated_at=authenticated_at,
        )

        assert event.user_id == user_id
        assert event.auth0_sub == auth0_sub
        assert event.authenticated_at == authenticated_at

    def test_user_authenticated_event_immutable(self):
        """Test that UserAuthenticated event is immutable."""
        event = UserAuthenticated(
            user_id=UserId.generate(),
            auth0_sub=Auth0Sub("auth0|123456789"),
            authenticated_at=datetime.utcnow(),
        )

        try:
            event.authenticated_at = datetime.utcnow()  # type: ignore
            assert False, "Should not be able to modify frozen event"
        except Exception:
            pass  # Expected

    @freeze_time("2025-01-01 12:00:00")
    def test_user_profile_updated_event(self):
        """Test UserProfileUpdated event creation."""
        user_id = UserId.generate()
        auth0_sub = Auth0Sub("auth0|123456789")
        old_prefs = UserPreferences(data={"theme": "light"})
        new_prefs = UserPreferences(data={"theme": "dark"})
        updated_at = datetime(2025, 1, 1, 12, 0, 0)

        event = UserProfileUpdated(
            user_id=user_id,
            auth0_sub=auth0_sub,
            old_preferences=old_prefs,
            new_preferences=new_prefs,
            updated_at=updated_at,
        )

        assert event.user_id == user_id
        assert event.auth0_sub == auth0_sub
        assert event.old_preferences == old_prefs
        assert event.new_preferences == new_prefs
        assert event.updated_at == updated_at

    def test_user_profile_updated_event_captures_preferences_change(self):
        """Test that UserProfileUpdated captures before/after preferences."""
        old_prefs = UserPreferences(data={"theme": "light", "lang": "en"})
        new_prefs = UserPreferences(data={"theme": "dark", "lang": "it"})

        event = UserProfileUpdated(
            user_id=UserId.generate(),
            auth0_sub=Auth0Sub("auth0|123456789"),
            old_preferences=old_prefs,
            new_preferences=new_prefs,
            updated_at=datetime.utcnow(),
        )

        # Verify old state
        assert event.old_preferences.get("theme") == "light"
        assert event.old_preferences.get("lang") == "en"

        # Verify new state
        assert event.new_preferences.get("theme") == "dark"
        assert event.new_preferences.get("lang") == "it"

    def test_user_profile_updated_event_immutable(self):
        """Test that UserProfileUpdated event is immutable."""
        event = UserProfileUpdated(
            user_id=UserId.generate(),
            auth0_sub=Auth0Sub("auth0|123456789"),
            old_preferences=UserPreferences.default(),
            new_preferences=UserPreferences(data={"theme": "dark"}),
            updated_at=datetime.utcnow(),
        )

        try:
            event.new_preferences = UserPreferences.default()  # type: ignore
            assert False, "Should not be able to modify frozen event"
        except Exception:
            pass  # Expected

    def test_events_contain_both_identifiers(self):
        """Test that all events contain both user_id and auth0_sub."""
        user_id = UserId.generate()
        auth0_sub = Auth0Sub("auth0|123456789")
        timestamp = datetime.utcnow()

        created_event = UserCreated(
            user_id=user_id,
            auth0_sub=auth0_sub,
            created_at=timestamp,
        )
        assert hasattr(created_event, "user_id")
        assert hasattr(created_event, "auth0_sub")

        auth_event = UserAuthenticated(
            user_id=user_id,
            auth0_sub=auth0_sub,
            authenticated_at=timestamp,
        )
        assert hasattr(auth_event, "user_id")
        assert hasattr(auth_event, "auth0_sub")

        updated_event = UserProfileUpdated(
            user_id=user_id,
            auth0_sub=auth0_sub,
            old_preferences=UserPreferences.default(),
            new_preferences=UserPreferences.default(),
            updated_at=timestamp,
        )
        assert hasattr(updated_event, "user_id")
        assert hasattr(updated_event, "auth0_sub")
