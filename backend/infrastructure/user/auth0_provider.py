"""Auth0 authentication provider implementation."""

import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
import jwt
from jwt import PyJWK
from jwt.exceptions import InvalidTokenError as JWTError, ExpiredSignatureError
from cachetools import TTLCache

from domain.user.auth.ports.auth_provider import (
    IAuthProvider,
    InvalidTokenError,
    JWKSError,
    Auth0APIError,
)
from domain.user.core.value_objects.auth0_sub import Auth0Sub


class Auth0Provider(IAuthProvider):
    """Auth0 authentication provider implementation.

    Handles JWT verification with JWKS caching and Auth0 Management API integration.

    Features:
    - RS256 JWT verification with JWKS
    - JWKS caching with 1-hour TTL
    - Audience and issuer validation
    - Auth0 Management API integration for user info

    Environment Variables:
    - AUTH0_DOMAIN: Auth0 tenant domain (e.g., "myapp.eu.auth0.com")
    - AUTH0_AUDIENCE: API identifier/audience
    - AUTH0_MANAGEMENT_CLIENT_ID: Management API client ID (optional)
    - AUTH0_MANAGEMENT_CLIENT_SECRET: Management API client secret (optional)

    Examples:
        >>> provider = Auth0Provider()
        >>> claims = await provider.verify_token(token)
        >>> user_info = await provider.get_user_info(Auth0Sub("auth0|123"))
    """

    def __init__(
        self,
        domain: Optional[str] = None,
        audience: Optional[str] = None,
        management_client_id: Optional[str] = None,
        management_client_secret: Optional[str] = None,
        jwks_cache_ttl: int = 3600,
    ):
        """Initialize Auth0 provider.

        Args:
            domain: Auth0 tenant domain (defaults to env AUTH0_DOMAIN)
            audience: API audience (defaults to env AUTH0_AUDIENCE)
            management_client_id: Management API client ID (optional)
            management_client_secret: Management API client secret (optional)
            jwks_cache_ttl: JWKS cache TTL in seconds (default: 3600 = 1h)

        Raises:
            ValueError: If required config is missing
        """
        self.domain = domain or os.getenv("AUTH0_DOMAIN")
        self.audience = audience or os.getenv("AUTH0_AUDIENCE")
        self.management_client_id = management_client_id or os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
        self.management_client_secret = management_client_secret or os.getenv(
            "AUTH0_MANAGEMENT_CLIENT_SECRET"
        )

        if not self.domain:
            raise ValueError("AUTH0_DOMAIN is required")
        if not self.audience:
            raise ValueError("AUTH0_AUDIENCE is required")

        # JWKS cache with TTL
        self.jwks_cache: TTLCache[str, Dict[str, Any]] = TTLCache(maxsize=10, ttl=jwks_cache_ttl)
        self._management_token: Optional[str] = None
        self._management_token_expires_at: Optional[datetime] = None

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token using Auth0 JWKS.

        Args:
            token: JWT token from Authorization header

        Returns:
            Decoded JWT claims dictionary containing:
            - sub: Auth0 subject identifier
            - aud: Audience
            - iss: Issuer
            - exp: Expiration timestamp
            - iat: Issued at timestamp

        Raises:
            InvalidTokenError: If token is invalid, expired, or malformed
            JWKSError: If JWKS fetching fails

        Examples:
            >>> claims = await provider.verify_token("eyJ...")
            >>> claims["sub"]
            'auth0|123456789'
        """
        try:
            # Decode header to get kid (key ID)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise InvalidTokenError("Token header missing 'kid'")

            # Get JWKS (cached)
            if kid not in self.jwks_cache:
                await self._refresh_jwks()

            rsa_key_dict = self.jwks_cache.get(kid)
            if not rsa_key_dict:
                raise InvalidTokenError(f"JWKS key {kid} not found")

            # Convert JWK dict to PyJWT format
            jwk = PyJWK.from_dict(rsa_key_dict)

            # Verify and decode token
            issuer = f"https://{self.domain}/"
            payload: Dict[str, Any] = jwt.decode(
                token,
                jwk.key,  # Use the key object from PyJWK
                algorithms=["RS256"],
                audience=self.audience,
                issuer=issuer,
            )

            return payload

        except ExpiredSignatureError as e:
            raise InvalidTokenError("Token has expired") from e
        except JWTError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}") from e
        except Exception as e:
            raise InvalidTokenError(f"Token verification failed: {str(e)}") from e

    async def get_user_info(self, auth0_sub: Auth0Sub) -> Dict[str, Any]:
        """Get user info from Auth0 Management API.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            User info dictionary containing:
            - email: User email
            - name: User name
            - picture: Profile picture URL
            - email_verified: Email verification status

        Raises:
            Auth0APIError: If API request fails

        Examples:
            >>> info = await provider.get_user_info(Auth0Sub("auth0|123"))
            >>> info["email"]
            'user@example.com'
        """
        # Ensure we have a valid management token
        await self._ensure_management_token()

        # Call Management API
        endpoint = f"/api/v2/users/{auth0_sub.value}"
        url = f"https://{self.domain}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self._management_token}"}
                timeout = aiohttp.ClientTimeout(total=10)

                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status == 404:
                        raise Auth0APIError(
                            endpoint, resp.status, f"User {auth0_sub.value} not found"
                        )
                    if resp.status >= 400:
                        text = await resp.text()
                        raise Auth0APIError(endpoint, resp.status, text)

                    user_info: Dict[str, Any] = await resp.json()
                    return user_info

        except aiohttp.ClientError as e:
            raise Auth0APIError(endpoint, 0, f"Network error: {str(e)}") from e

    async def _refresh_jwks(self) -> None:
        """Refresh JWKS from Auth0 well-known endpoint.

        Raises:
            JWKSError: If JWKS fetching fails
        """
        jwks_url = f"https://{self.domain}/.well-known/jwks.json"

        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=5)
                async with session.get(jwks_url, timeout=timeout) as resp:
                    resp.raise_for_status()
                    jwks = await resp.json()

            # Cache RSA keys by kid
            for key in jwks.get("keys", []):
                kid = key.get("kid")
                if not kid:
                    continue

                # Build RSA key dict for PyJWT (compatible format)
                # PyJWT accetta direttamente il dict JWK
                rsa_key = key

                self.jwks_cache[kid] = rsa_key

        except aiohttp.ClientError as e:
            raise JWKSError(f"Failed to fetch JWKS: {str(e)}") from e
        except Exception as e:
            raise JWKSError(f"Failed to parse JWKS: {str(e)}") from e

    async def _ensure_management_token(self) -> None:
        """Ensure we have a valid Management API token.

        Requests a new token if:
        - No token exists
        - Current token is expired or about to expire (< 5 min)

        Raises:
            Auth0APIError: If token request fails
        """
        # Check if we need a new token
        now = datetime.utcnow()
        if self._management_token and self._management_token_expires_at:
            # Token valid for at least 5 more minutes
            if self._management_token_expires_at > now + timedelta(minutes=5):
                return

        # Check if Management API credentials are configured
        if not self.management_client_id or not self.management_client_secret:
            raise Auth0APIError(
                "/oauth/token",
                0,
                "Management API credentials not configured "
                "(AUTH0_MANAGEMENT_CLIENT_ID, AUTH0_MANAGEMENT_CLIENT_SECRET)",
            )

        # Request new token
        endpoint = "/oauth/token"
        url = f"https://{self.domain}{endpoint}"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.management_client_id,
            "client_secret": self.management_client_secret,
            "audience": f"https://{self.domain}/api/v2/",
        }

        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.post(url, json=payload, timeout=timeout) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise Auth0APIError(endpoint, resp.status, text)

                    data = await resp.json()
                    self._management_token = data["access_token"]
                    expires_in = data.get("expires_in", 86400)  # Default 24h
                    self._management_token_expires_at = now + timedelta(seconds=expires_in)

        except aiohttp.ClientError as e:
            raise Auth0APIError(endpoint, 0, f"Network error: {str(e)}") from e
        except KeyError as e:
            raise Auth0APIError(endpoint, 0, f"Invalid token response: {str(e)}") from e
