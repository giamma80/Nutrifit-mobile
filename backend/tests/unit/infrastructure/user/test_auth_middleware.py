"""Unit tests for AuthMiddleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse

from infrastructure.user.auth_middleware import AuthMiddleware
from infrastructure.user.auth0_provider import Auth0Provider
from domain.user.auth.ports.auth_provider import InvalidTokenError, JWKSError


class TestAuthMiddleware:
    """Test AuthMiddleware implementation."""

    @pytest.fixture
    def mock_auth_provider(self):
        """Create mock Auth0Provider."""
        provider = MagicMock(spec=Auth0Provider)
        provider.verify_token = AsyncMock()
        return provider

    @pytest.fixture
    def app(self):
        """Create FastAPI test app."""
        return FastAPI()

    @pytest.fixture
    def middleware(self, app, mock_auth_provider):
        """Create AuthMiddleware instance."""
        return AuthMiddleware(app, auth_provider=mock_auth_provider)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = MagicMock()
        return request

    @pytest.mark.asyncio
    async def test_successful_authentication(self, middleware, mock_request, mock_auth_provider):
        """Test successful token verification."""
        mock_request.headers = {"Authorization": "Bearer valid_token"}
        mock_claims = {"sub": "auth0|123456789", "aud": "https://api.test.com"}
        mock_auth_provider.verify_token.return_value = mock_claims

        async def mock_call_next(req):
            return JSONResponse(content={"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert mock_request.state.auth_claims == mock_claims
        mock_auth_provider.verify_token.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_missing_authorization_header_with_auth_required(
        self, middleware, mock_request, mock_auth_provider
    ):
        """Test missing Authorization header when auth is required."""
        middleware.auth_required = True
        mock_request.headers = {}

        async def mock_call_next(req):
            return JSONResponse(content={"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 401
        body = response.body.decode()
        assert "Missing authorization token" in body

    @pytest.mark.asyncio
    async def test_missing_authorization_header_without_auth_required(
        self, middleware, mock_request, mock_auth_provider
    ):
        """Test missing Authorization header when auth is not required."""
        middleware.auth_required = False
        mock_request.headers = {}

        async def mock_call_next(req):
            return JSONResponse(content={"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert mock_request.state.auth_claims is None

    @pytest.mark.asyncio
    async def test_invalid_token_format(self, middleware, mock_request, mock_auth_provider):
        """Test invalid token format (not Bearer)."""
        middleware.auth_required = True
        mock_request.headers = {"Authorization": "Invalid token_format"}

        async def mock_call_next(req):
            return JSONResponse(content={"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_verification_failure(self, middleware, mock_request, mock_auth_provider):
        """Test token verification failure."""
        mock_request.headers = {"Authorization": "Bearer invalid_token"}
        mock_auth_provider.verify_token.side_effect = InvalidTokenError("Token expired")

        async def mock_call_next(req):
            return JSONResponse(content={"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 401
        body = response.body.decode()
        assert "invalid_token" in body

    @pytest.mark.asyncio
    async def test_jwks_error(self, middleware, mock_request, mock_auth_provider):
        """Test JWKS fetching error."""
        mock_request.headers = {"Authorization": "Bearer some_token"}
        mock_auth_provider.verify_token.side_effect = JWKSError("Failed to fetch JWKS")

        async def mock_call_next(req):
            return JSONResponse(content={"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 500
        body = response.body.decode()
        assert "authentication_error" in body

    def test_extract_token_success(self, middleware):
        """Test successful token extraction."""
        token = middleware._extract_token("Bearer eyJ...")

        assert token == "eyJ..."

    def test_extract_token_no_bearer(self, middleware):
        """Test token extraction without Bearer prefix."""
        token = middleware._extract_token("eyJ...")

        assert token is None

    def test_extract_token_wrong_format(self, middleware):
        """Test token extraction with wrong format."""
        token = middleware._extract_token("Bearer token with spaces")

        assert token is None

    def test_extract_token_empty(self, middleware):
        """Test token extraction with empty header."""
        token = middleware._extract_token("")

        assert token is None

    def test_extract_token_none(self, middleware):
        """Test token extraction with None header."""
        token = middleware._extract_token(None)

        assert token is None

    def test_init_with_auth_required_env_true(self, app, mock_auth_provider):
        """Test initialization with AUTH_REQUIRED=true."""
        with patch.dict("os.environ", {"AUTH_REQUIRED": "true"}):
            middleware = AuthMiddleware(app, auth_provider=mock_auth_provider)
            assert middleware.auth_required is True

    def test_init_with_auth_required_env_false(self, app, mock_auth_provider):
        """Test initialization with AUTH_REQUIRED=false."""
        with patch.dict("os.environ", {"AUTH_REQUIRED": "false"}):
            middleware = AuthMiddleware(app, auth_provider=mock_auth_provider)
            assert middleware.auth_required is False

    def test_init_without_auth_required_env(self, app):
        """Test initialization without AUTH_REQUIRED env (defaults to true)."""
        with patch.dict("os.environ", {}, clear=True):
            with patch.dict(
                "os.environ", {"AUTH0_DOMAIN": "test.auth0.com", "AUTH0_AUDIENCE": "test"}
            ):
                middleware = AuthMiddleware(app)
                assert middleware.auth_required is True

    @pytest.mark.asyncio
    async def test_bearer_case_insensitive(self, middleware, mock_request, mock_auth_provider):
        """Test that Bearer scheme is case-insensitive."""
        mock_request.headers = {"Authorization": "bearer valid_token"}
        mock_claims = {"sub": "auth0|123456789"}
        mock_auth_provider.verify_token.return_value = mock_claims

        async def mock_call_next(req):
            return JSONResponse(content={"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        mock_auth_provider.verify_token.assert_called_once_with("valid_token")
