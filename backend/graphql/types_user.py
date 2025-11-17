"""GraphQL types for User domain."""

from typing import Optional, cast
from datetime import datetime
import strawberry

from domain.user.core.entities.user import User
from domain.user.core.value_objects.user_preferences import UserPreferences


@strawberry.type
class UserPreferencesType:
    """User preferences GraphQL type.

    Application-specific user preferences (theme, language, notifications, etc.).
    Stored as JSON object in backend.

    Examples:
        {
          "theme": "dark",
          "language": "it",
          "notifications": true
        }
    """

    @strawberry.field
    def data(self, root: UserPreferences) -> strawberry.scalars.JSON:
        """Get preferences as JSON object.

        Returns:
            JSON object with preferences
        """
        return root.data


@strawberry.type
class UserType:
    """User GraphQL type.

    Represents authenticated user with app-specific data.
    Auth0 profile data (email, name, etc.) managed separately.

    Examples:
        query {
          me {
            userId
            auth0Sub
            preferences { data }
            isActive
            createdAt
          }
        }
    """

    @strawberry.field
    def user_id(self, root: User) -> str:
        """Internal user UUID.

        Returns:
            UUID string
        """
        return str(root.user_id)

    @strawberry.field
    def auth0_sub(self, root: User) -> str:
        """Auth0 subject identifier.

        Format: {provider}|{provider_user_id}
        Examples: auth0|123, google-oauth2|456, facebook|789

        Returns:
            Auth0 subject string
        """
        return str(root.auth0_sub)

    @strawberry.field
    def preferences(self, root: User) -> UserPreferencesType:
        """User preferences.

        Returns:
            User preferences object
        """
        return cast(UserPreferencesType, root.preferences)

    @strawberry.field
    def created_at(self, root: User) -> datetime:
        """User creation timestamp.

        Returns:
            UTC datetime
        """
        return root.created_at

    @strawberry.field
    def updated_at(self, root: User) -> datetime:
        """Last update timestamp.

        Returns:
            UTC datetime
        """
        return root.updated_at

    @strawberry.field
    def last_authenticated_at(self, root: User) -> Optional[datetime]:
        """Last authentication timestamp.

        Returns:
            UTC datetime or None
        """
        return root.last_authenticated_at

    @strawberry.field
    def is_active(self, root: User) -> bool:
        """Account active status.

        Inactive users cannot authenticate.

        Returns:
            True if active, False otherwise
        """
        return root.is_active


@strawberry.input
class UserPreferencesInput:
    """Input type for user preferences.

    Examples:
        mutation {
          updatePreferences(preferences: {
            theme: "dark"
            language: "it"
            notifications: true
          }) {
            userId
            preferences { data }
          }
        }
    """

    data: strawberry.scalars.JSON = strawberry.field(
        default_factory=dict,
        description="Preferences as JSON object",
    )

    def to_domain(self) -> UserPreferences:
        """Convert to domain value object.

        Returns:
            UserPreferences domain object
        """
        return UserPreferences(data=self.data)
