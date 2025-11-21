"""Auth middleware for JWT verification with Auth0."""

import os
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from functools import lru_cache
from datetime import datetime, timedelta

security = HTTPBearer()


class Auth0Config:
    """Auth0 configuration."""

    def __init__(self):
        self.domain = os.getenv("AUTH0_DOMAIN")
        self.audience = os.getenv("AUTH0_AUDIENCE")
        self.algorithms = ["RS256"]

        if not self.domain or not self.audience:
            raise ValueError("AUTH0_DOMAIN and AUTH0_AUDIENCE must be set")


@lru_cache()
def get_auth0_config() -> Auth0Config:
    """Get cached Auth0 configuration."""
    return Auth0Config()


class JWKSCache:
    """Cache for Auth0 JWKS with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        self.jwks: Optional[Dict[str, Any]] = None
        self.expires_at: Optional[datetime] = None
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Check if cache is expired."""
        if not self.expires_at:
            return True
        return datetime.utcnow() >= self.expires_at

    async def get_jwks(self, domain: str) -> Dict[str, Any]:
        """Get JWKS from cache or fetch from Auth0."""
        if self.is_expired():
            await self.refresh_jwks(domain)
        return self.jwks or {}

    async def refresh_jwks(self, domain: str) -> None:
        """Fetch JWKS from Auth0."""
        url = f"https://{domain}/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            self.jwks = response.json()
            self.expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)


# Global JWKS cache
jwks_cache = JWKSCache()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """Verify JWT token from Auth0.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        Decoded JWT payload with user claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    config = get_auth0_config()

    try:
        # Get unverified header to find kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header missing 'kid'",
            )

        # Get JWKS from cache
        jwks = await jwks_cache.get_jwks(config.domain)

        # Find matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key["kid"] == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unable to find key with kid: {kid}",
            )

        # Verify and decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=config.algorithms,
            audience=config.audience,
            issuer=f"https://{config.domain}/",
        )

        # Add original token to payload (for MCP servers)
        payload["_token"] = token

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}",
        ) from e


async def get_current_user(payload: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """Get current authenticated user from JWT payload.

    Args:
        payload: Verified JWT payload

    Returns:
        User data dictionary with sub, token, and other claims
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )

    # Automatic user onboarding: check/create user in Nutrifit DB
    token = payload.get("_token")
    graphql_endpoint = os.getenv("GRAPHQL_ENDPOINT", "http://nutrifit-backend:8080/graphql")
    nutrifit_user_id = None
    
    try:
        async with httpx.AsyncClient() as client:
            # Check if user exists
            check_response = await client.post(
                graphql_endpoint,
                json={"query": "query { user { exists } }"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            check_data = check_response.json()
            exists = check_data.get("data", {}).get("user", {}).get("exists", False)
            
            if exists:
                # Get existing user ID
                me_response = await client.post(
                    graphql_endpoint,
                    json={"query": "query { user { me { userId } } }"},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                me_data = me_response.json()
                nutrifit_user_id = me_data.get("data", {}).get("user", {}).get("me", {}).get("userId")
                print(f"✅ Existing Nutrifit user: {nutrifit_user_id} (Auth0: {user_id})")
            else:
                # Create new user via authenticate
                create_response = await client.post(
                    graphql_endpoint,
                    json={"query": "mutation { user { authenticate { userId } } }"},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                create_data = create_response.json()
                nutrifit_user_id = create_data.get("data", {}).get("user", {}).get("authenticate", {}).get("userId")
                print(f"🆕 Created Nutrifit user: {nutrifit_user_id} (Auth0: {user_id})")
    except Exception as e:
        print(f"⚠️ Onboarding failed for {user_id}: {e}")
        # Continue without nutrifit_user_id - agent will handle gracefully

    return {
        "user_id": user_id,
        "nutrifit_user_id": nutrifit_user_id,  # Nutrifit UUID (may be None if error)
        "token": token,
        "email": payload.get("email"),
        "email_verified": payload.get("email_verified"),
        "permissions": payload.get("permissions", []),
        "scope": payload.get("scope", ""),
    }


def require_permissions(*required_permissions: str):
    """Dependency to check if user has required permissions.

    Usage:
        @app.get("/admin", dependencies=[Depends(require_permissions("admin:read"))])
    """

    async def check_permissions(user: Dict[str, Any] = Depends(get_current_user)):
        user_permissions = set(user.get("permissions", []))
        missing = set(required_permissions) - user_permissions

        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing)}",
            )

        return user

    return check_permissions
