"""FastAPI authentication middleware."""

import os
from typing import Optional, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from infrastructure.user.auth0_provider import Auth0Provider
from domain.user.auth.ports.auth_provider import InvalidTokenError, JWKSError


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for JWT authentication.

    Verifies JWT tokens from Authorization header and sets auth claims
    in request.state for downstream handlers.

    Features:
    - Bearer token extraction
    - JWT verification via Auth0Provider
    - Optional authentication (configurable)
    - Sets request.state.auth_claims for authenticated requests

    Environment Variables:
    - AUTH_REQUIRED: "true" to require auth on all routes (default: "true")

    Examples:
        >>> app.add_middleware(AuthMiddleware)
        >>> # In route handler:
        >>> auth_claims = request.state.auth_claims
        >>> user_sub = auth_claims["sub"]
    """

    def __init__(self, app: Any, auth_provider: Optional[Auth0Provider] = None) -> None:
        """Initialize middleware.

        Args:
            app: FastAPI application
            auth_provider: Auth0Provider instance (optional, creates new if None)
        """
        super().__init__(app)
        self.auth_provider = auth_provider or Auth0Provider()
        self.auth_required = os.getenv("AUTH_REQUIRED", "true").lower() == "true"

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process request and verify JWT token.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler in chain

        Returns:
            Response from handler or 401/500 error
        """
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        token = self._extract_token(auth_header)

        # Handle missing token
        if not token:
            if self.auth_required:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "unauthorized", "message": "Missing authorization token"},
                )
            # Auth not required - proceed without claims
            request.state.auth_claims = None
            return await call_next(request)

        # Verify token
        try:
            claims = await self.auth_provider.verify_token(token)
            request.state.auth_claims = claims

        except InvalidTokenError as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "invalid_token", "message": str(e)},
            )

        except JWKSError:
            # JWKS error is a server error (not client's fault)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "authentication_error",
                    "message": "Authentication service error",
                },
            )

        # Proceed to next handler
        return await call_next(request)

    def _extract_token(self, auth_header: Optional[str]) -> Optional[str]:
        """Extract Bearer token from Authorization header.

        Args:
            auth_header: Authorization header value

        Returns:
            JWT token or None

        Examples:
            >>> self._extract_token("Bearer eyJ...")
            'eyJ...'
            >>> self._extract_token("eyJ...")  # Missing Bearer
            None
        """
        if not auth_header:
            return None

        parts = auth_header.split()

        if len(parts) != 2:
            return None

        scheme, token = parts

        if scheme.lower() != "bearer":
            return None

        return token
