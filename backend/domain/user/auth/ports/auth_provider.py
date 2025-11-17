"""Authentication provider port (interface)."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from domain.user.core.value_objects.auth0_sub import Auth0Sub


class IAuthProvider(ABC):
    """Authentication provider interface.

    Abstracts Auth0 integration. Allows mocking in tests and
    potential migration to different auth providers.

    Examples:
        >>> # Implementation example (not actual usage)
        >>> class Auth0Provider(IAuthProvider):
        ...     async def verify_token(self, token: str) -> Dict[str, Any]:
        ...         # Verify JWT with Auth0 JWKS
        ...         pass
    """

    @abstractmethod
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return claims.

        Args:
            token: JWT access token from Authorization header

        Returns:
            Token claims dictionary with at minimum:
            - sub: Auth0 subject identifier
            - email: User email (optional)
            - email_verified: Email verification status (optional)
            - aud: Audience (must match API_AUDIENCE)
            - iss: Issuer (must match Auth0 domain)
            - exp: Expiration timestamp

        Raises:
            InvalidTokenError: Token is invalid, expired, or has wrong audience
            JWKSError: Cannot fetch or verify with Auth0 public keys

        Examples:
            >>> provider = Auth0Provider()
            >>> claims = await provider.verify_token(token)
            >>> print(claims["sub"])  # 'auth0|123456'
            >>> print(claims["email"])  # 'user@example.com'

        Note:
            Implementation should:
            - Verify signature with JWKS (RS256)
            - Validate audience (API_AUDIENCE)
            - Validate issuer (https://{domain}/)
            - Check expiration
            - Cache JWKS for performance (1h TTL recommended)
        """
        pass

    @abstractmethod
    async def get_user_info(self, auth0_sub: Auth0Sub) -> Dict[str, Any]:
        """Get user profile from Auth0 /userinfo endpoint.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            User profile dictionary with:
            - sub: Auth0 subject
            - email: User email
            - name: Full name
            - picture: Profile picture URL
            - email_verified: Email verification status
            - Additional standard OIDC claims

        Raises:
            UserNotFoundError: User does not exist in Auth0
            Auth0APIError: Auth0 API request failed

        Examples:
            >>> auth0_sub = Auth0Sub("auth0|123456")
            >>> profile = await provider.get_user_info(auth0_sub)
            >>> print(profile["email"])
            'user@example.com'

        Note:
            Requires Auth0 Management API token with read:users scope.
            Consider caching responses (TTL 5-15 minutes).
        """
        pass


class InvalidTokenError(Exception):
    """Token verification failed."""

    def __init__(self, reason: str):
        """Initialize with failure reason.

        Args:
            reason: Human-readable reason for failure
        """
        self.reason = reason
        super().__init__(f"Invalid token: {reason}")


class JWKSError(Exception):
    """JWKS fetching or processing failed."""

    def __init__(self, reason: str):
        """Initialize with failure reason.

        Args:
            reason: Human-readable reason for failure
        """
        self.reason = reason
        super().__init__(f"JWKS error: {reason}")


class Auth0APIError(Exception):
    """Auth0 API request failed."""

    def __init__(self, endpoint: str, status_code: int, message: str):
        """Initialize with API error details.

        Args:
            endpoint: Auth0 API endpoint that failed
            status_code: HTTP status code
            message: Error message from Auth0
        """
        self.endpoint = endpoint
        self.status_code = status_code
        self.message = message
        super().__init__(f"Auth0 API error at {endpoint} " f"(HTTP {status_code}): {message}")
