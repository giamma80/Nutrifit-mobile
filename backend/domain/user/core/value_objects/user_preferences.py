"""UserPreferences value object."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class UserPreferences:
    """User application preferences value object.

    Stores app-specific settings (not Auth0 profile data).
    Immutable - use `with_value()` to create modified copies.

    Examples:
        >>> prefs = UserPreferences.default()
        >>> prefs.data
        {}

        >>> prefs = UserPreferences(data={"theme": "dark", "language": "it"})
        >>> prefs.get("theme")
        'dark'

        >>> prefs2 = prefs.with_value("notifications", True)
        >>> prefs2.data
        {'theme': 'dark', 'language': 'it', 'notifications': True}

    Note:
        This value object is immutable. Each modification returns a new instance.
    """

    data: Dict[str, Any]

    def __post_init__(self) -> None:
        """Validate preferences data."""
        if not isinstance(self.data, dict):
            raise TypeError("Preferences data must be a dictionary")

        # Validate that data is JSON-serializable (no complex objects)
        try:
            import json

            json.dumps(self.data)
        except (TypeError, ValueError) as e:
            raise ValueError("Preferences data must be JSON-serializable") from e

    @staticmethod
    def default() -> "UserPreferences":
        """Create default empty preferences.

        Returns:
            UserPreferences with empty data dictionary
        """
        return UserPreferences(data={})

    def get(self, key: str, default: Any = None) -> Any:
        """Get preference value by key.

        Args:
            key: Preference key
            default: Default value if key not found

        Returns:
            Preference value or default

        Examples:
            >>> prefs = UserPreferences(data={"theme": "dark"})
            >>> prefs.get("theme")
            'dark'
            >>> prefs.get("missing", "default_value")
            'default_value'
        """
        return self.data.get(key, default)

    def with_value(self, key: str, value: Any) -> "UserPreferences":
        """Return new preferences with updated value (immutable).

        Args:
            key: Preference key to update
            value: New value for the key

        Returns:
            New UserPreferences instance with updated data

        Examples:
            >>> prefs = UserPreferences.default()
            >>> prefs2 = prefs.with_value("theme", "dark")
            >>> prefs2.get("theme")
            'dark'
            >>> prefs.get("theme")  # Original unchanged
            None

        Note:
            Original instance remains unchanged (immutability).
        """
        new_data = self.data.copy()
        new_data[key] = value
        return UserPreferences(data=new_data)

    def with_values(self, updates: Dict[str, Any]) -> "UserPreferences":
        """Return new preferences with multiple updated values.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            New UserPreferences instance with updated data

        Examples:
            >>> prefs = UserPreferences.default()
            >>> updates = {"theme": "dark", "language": "it"}
            >>> prefs2 = prefs.with_values(updates)
            >>> prefs2.data
            {'theme': 'dark', 'language': 'it'}
        """
        new_data = self.data.copy()
        new_data.update(updates)
        return UserPreferences(data=new_data)

    def without_key(self, key: str) -> "UserPreferences":
        """Return new preferences with key removed.

        Args:
            key: Preference key to remove

        Returns:
            New UserPreferences instance without the key

        Examples:
            >>> prefs = UserPreferences(data={"theme": "dark", "lang": "it"})
            >>> prefs2 = prefs.without_key("theme")
            >>> prefs2.data
            {'lang': 'it'}
        """
        new_data = self.data.copy()
        new_data.pop(key, None)
        return UserPreferences(data=new_data)

    def __contains__(self, key: str) -> bool:
        """Check if preference key exists.

        Examples:
            >>> prefs = UserPreferences(data={"theme": "dark"})
            >>> "theme" in prefs
            True
            >>> "missing" in prefs
            False
        """
        return key in self.data

    def __len__(self) -> int:
        """Return number of preferences.

        Examples:
            >>> prefs = UserPreferences(data={"theme": "dark", "lang": "it"})
            >>> len(prefs)
            2
        """
        return len(self.data)
