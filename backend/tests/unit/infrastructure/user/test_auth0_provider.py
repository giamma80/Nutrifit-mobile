"""Unit tests for Auth0Provider with mocked HTTP calls."""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from infrastructure.user.auth0_provider import Auth0Provider
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.auth.ports.auth_provider import (
    InvalidTokenError,
    JWKSError,
    Auth0APIError,
)


class TestAuth0Provider:
    """Test Auth0Provider implementation with mocked dependencies."""

    @pytest.fixture
    def provider(self):
        """Create Auth0Provider with test config."""
        return Auth0Provider(
            domain="test.auth0.com",
            audience="https://api.test.com",
            management_client_id="test_client_id",
            management_client_secret="test_client_secret",
        )

    def test_init_with_env_vars(self):
        """Test initialization from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "AUTH0_DOMAIN": "test.auth0.com",
                "AUTH0_AUDIENCE": "https://api.test.com",
            },
        ):
            provider = Auth0Provider()
            assert provider.domain == "test.auth0.com"
            assert provider.audience == "https://api.test.com"

    def test_init_without_domain_raises_error(self):
        """Test that missing domain raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="AUTH0_DOMAIN is required"):
                Auth0Provider(domain=None, audience="https://api.test.com")

    def test_init_without_audience_raises_error(self):
        """Test that missing audience raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="AUTH0_AUDIENCE is required"):
                Auth0Provider(domain="test.auth0.com", audience=None)

    @pytest.mark.asyncio
    async def test_verify_token_success(self, provider):
        """Test successful token verification."""
        mock_claims = {
            "sub": "auth0|123456789",
            "aud": "https://api.test.com",
            "iss": "https://test.auth0.com/",
            "exp": 9999999999,
            "iat": 1234567890,
        }

        with patch("infrastructure.user.auth0_provider.jwt.get_unverified_header") as mock_header:
            with patch("infrastructure.user.auth0_provider.PyJWK") as mock_pyjwk:
                with patch("infrastructure.user.auth0_provider.jwt.decode") as mock_decode:
                    mock_header.return_value = {"kid": "test_kid"}
                    mock_decode.return_value = mock_claims

                    # Mock PyJWK.from_dict to return a mock with .key attribute
                    mock_jwk_instance = MagicMock()
                    mock_jwk_instance.key = "mock_key"
                    mock_pyjwk.from_dict.return_value = mock_jwk_instance

                    provider.jwks_cache["test_kid"] = {"kty": "RSA", "kid": "test_kid"}

                    claims = await provider.verify_token("test_token")

                    assert claims == mock_claims
                    mock_decode.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_token_missing_kid(self, provider):
        """Test token verification fails when kid is missing."""
        with patch("infrastructure.user.auth0_provider.jwt.get_unverified_header") as mock_header:
            mock_header.return_value = {}  # No kid

            with pytest.raises(InvalidTokenError, match="missing 'kid'"):
                await provider.verify_token("test_token")

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, provider):
        """Test token verification fails for expired token."""
        with patch("infrastructure.user.auth0_provider.jwt.get_unverified_header") as mock_header:
            with patch("infrastructure.user.auth0_provider.PyJWK") as mock_pyjwk:
                with patch("infrastructure.user.auth0_provider.jwt.decode") as mock_decode:
                    from jwt.exceptions import ExpiredSignatureError

                    mock_header.return_value = {"kid": "test_kid"}
                    mock_decode.side_effect = ExpiredSignatureError("Token expired")

                    # Mock PyJWK.from_dict
                    mock_jwk_instance = MagicMock()
                    mock_jwk_instance.key = "mock_key"
                    mock_pyjwk.from_dict.return_value = mock_jwk_instance

                    provider.jwks_cache["test_kid"] = {"kty": "RSA"}

                    with pytest.raises(InvalidTokenError, match="expired"):
                        await provider.verify_token("test_token")

    @pytest.mark.asyncio
    async def test_refresh_jwks_success(self, provider):
        """Test successful JWKS refresh."""
        mock_jwks = {
            "keys": [
                {
                    "kid": "test_kid_1",
                    "kty": "RSA",
                    "use": "sig",
                    "n": "test_n",
                    "e": "AQAB",
                }
            ]
        }

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_jwks)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_get = AsyncMock(return_value=mock_response)
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await provider._refresh_jwks()

            assert "test_kid_1" in provider.jwks_cache
            assert provider.jwks_cache["test_kid_1"]["kty"] == "RSA"

    @pytest.mark.asyncio
    async def test_refresh_jwks_network_error(self, provider):
        """Test JWKS refresh handles network errors."""
        import aiohttp

        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(JWKSError, match="Failed to fetch JWKS"):
                await provider._refresh_jwks()

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, provider):
        """Test successful user info retrieval."""
        mock_user_data = {
            "user_id": "auth0|123456789",
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
        }

        provider._management_token = "test_management_token"
        provider._management_token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_user_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_get = AsyncMock(return_value=mock_response)
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            user_info = await provider.get_user_info(Auth0Sub("auth0|123456789"))

            assert user_info == mock_user_data

    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self, provider):
        """Test user info retrieval for non-existent user."""
        provider._management_token = "test_management_token"
        provider._management_token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="User not found")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_get = AsyncMock(return_value=mock_response)
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(Auth0APIError, match="not found"):
                await provider.get_user_info(Auth0Sub("auth0|nonexistent"))

    @pytest.mark.asyncio
    async def test_ensure_management_token_requests_new_token(self, provider):
        """Test that management token is requested when needed."""
        mock_token_response = {
            "access_token": "new_management_token",
            "expires_in": 86400,
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_token_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_post = AsyncMock(return_value=mock_response)
        mock_post.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_post)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await provider._ensure_management_token()

            assert provider._management_token == "new_management_token"
            assert provider._management_token_expires_at is not None

    @pytest.mark.asyncio
    async def test_ensure_management_token_without_credentials(self, provider):
        """Test that missing Management API credentials raises error."""
        provider.management_client_id = None
        provider.management_client_secret = None

        with pytest.raises(Auth0APIError, match="credentials not configured"):
            await provider._ensure_management_token()

    @pytest.mark.asyncio
    async def test_ensure_management_token_reuses_valid_token(self, provider):
        """Test that valid management token is reused."""
        provider._management_token = "existing_token"
        provider._management_token_expires_at = datetime.utcnow() + timedelta(hours=1)

        # Should not make HTTP request
        with patch("aiohttp.ClientSession") as mock_session:
            await provider._ensure_management_token()

            # Session should not be created
            mock_session.assert_not_called()
