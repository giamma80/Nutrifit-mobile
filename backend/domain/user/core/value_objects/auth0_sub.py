"""Auth0Sub value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Auth0Sub:
    """Auth0 subject identifier value object.

    Represents the unique identifier from Auth0 (sub claim in JWT).
    Format: <provider>|<id>

    Examples:
        >>> auth0_sub = Auth0Sub("auth0|123456789")
        >>> auth0_sub.value
        'auth0|123456789'

        >>> auth0_sub = Auth0Sub("google-oauth2|987654321")
        >>> auth0_sub.provider
        'google-oauth2'

    Raises:
        ValueError: If format is invalid (missing pipe or too long)
    """

    value: str

    def __post_init__(self) -> None:
        """Validate Auth0 sub format.

        Supports two formats:
        1. User authentication: <provider>|<id> (e.g., "auth0|123", "google-oauth2|456")
        2. Client credentials (M2M): <client_id>@clients (e.g., "abc123@clients")
        """
        if not self.value:
            raise ValueError("Auth0 sub cannot be empty")

        # Accept both formats: provider|id OR client_id@clients
        if "|" not in self.value and "@clients" not in self.value:
            raise ValueError(
                f"Invalid Auth0 sub format: {self.value}. "
                "Expected format: <provider>|<id> or <client_id>@clients"
            )

        if len(self.value) > 255:
            raise ValueError(
                f"Auth0 sub too long ({len(self.value)} chars). " "Maximum 255 characters allowed"
            )

    @property
    def provider(self) -> str:
        """Extract provider from Auth0 sub.

        Returns:
            Provider name (e.g., 'auth0', 'google-oauth2', 'facebook', 'clients')

        Examples:
            >>> Auth0Sub("auth0|123").provider
            'auth0'
            >>> Auth0Sub("google-oauth2|456").provider
            'google-oauth2'
            >>> Auth0Sub("abc123@clients").provider
            'clients'
        """
        if "@clients" in self.value:
            return "clients"
        return self.value.split("|", 1)[0]

    @property
    def external_id(self) -> str:
        """Extract external ID from Auth0 sub.

        Returns:
            External provider's user ID or client ID

        Examples:
            >>> Auth0Sub("auth0|123").external_id
            '123'
            >>> Auth0Sub("abc123@clients").external_id
            'abc123'
        """
        if "@clients" in self.value:
            return self.value.split("@", 1)[0]
        return self.value.split("|", 1)[1]

    @property
    def is_client(self) -> bool:
        """Check if this sub represents a client credentials (M2M) token.

        Returns:
            True if sub is from client_credentials grant, False otherwise

        Examples:
            >>> Auth0Sub("auth0|123").is_client
            False
            >>> Auth0Sub("abc123@clients").is_client
            True
        """
        return "@clients" in self.value

    def __str__(self) -> str:
        """String representation returns the value."""
        return self.value

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"Auth0Sub('{self.value}')"
