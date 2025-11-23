#!/usr/bin/env python3
"""
Nutrifit User MCP Server (FastMCP)

Model Context Protocol server for user authentication and profile management.
Refactored with FastMCP for cleaner, type-safe tool definitions.

IMPORTANT FOR AI ASSISTANTS:
==========================
This server provides 6 tools for user management:

🔐 AUTHENTICATION & QUERIES:
1. get_current_user() - Get authenticated user profile
2. check_user_exists(auth0_sub) - Verify if user exists by Auth0 ID
3. get_user_by_id(user_id) - Get user profile by UUID

✏️ MUTATIONS:
4. authenticate_or_create(auth0_sub, email, name) - First login/create user
5. update_preferences(language, theme, notifications) - Update user settings
6. deactivate_account() - Soft delete account

CRITICAL: Most tools require JWT token via AUTH0_TOKEN environment variable.
"""

import os
from typing import Optional

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field


# Configuration
GRAPHQL_ENDPOINT = os.getenv("GRAPHQL_ENDPOINT", "http://localhost:8080/graphql")
DEFAULT_TIMEOUT = 30.0

# Initialize FastMCP
mcp = FastMCP("Nutrifit User Management")


async def graphql_query(
    query: str,
    variables: Optional[dict] = None,
    require_auth: bool = False
) -> dict:
    """Execute GraphQL query against Nutrifit backend."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    headers = {"Content-Type": "application/json"}
    
    if require_auth:
        auth_token = os.getenv("AUTH0_TOKEN")
        if not auth_token:
            raise Exception("AUTH0_TOKEN required for authenticated requests")
        headers["Authorization"] = f"Bearer {auth_token}"

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(GRAPHQL_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

    if "errors" in result:
        errors = [err.get("message", str(err)) for err in result["errors"]]
        raise Exception(f"GraphQL errors: {'; '.join(errors)}")

    return result["data"]


# Tool 1: Get Current User
@mcp.tool()
async def get_current_user() -> dict:
    """🔐 Get authenticated user profile with preferences and settings.
    
    Use this to retrieve the current logged-in user's complete profile.
    Requires valid JWT token in AUTH0_TOKEN environment variable.
    
    Returns:
        Complete user profile:
        - id: User UUID
        - auth0Sub: Auth0 identifier
        - email, name: Basic info
        - language, theme, notificationsEnabled: Preferences
        - isActive, createdAt, updatedAt: Metadata
    
    Raises:
        Exception: If AUTH0_TOKEN is missing or invalid
    """
    query = """
    query GetCurrentUser {
        user {
            me {
                userId
                auth0Sub
                preferences {
                    data
                }
                createdAt
                updatedAt
                lastAuthenticatedAt
                isActive
            }
        }
    }
    """
    data = await graphql_query(query, require_auth=True)
    return data["user"]["me"]


# Tool 2: Check User Exists
@mcp.tool()
async def check_user_exists(auth0_sub: str) -> bool:
    """✓ Check if user exists in database by Auth0 ID.
    
    Use this before authenticate_or_create to verify if account exists.
    Does NOT require authentication - public query.
    
    Args:
        auth0_sub: Auth0 subject identifier
            Format: "auth0|123456" or "google-oauth2|123456"
    
    Returns:
        True if user exists in database
        False if user needs to be created
    
    Example:
        exists = await check_user_exists("auth0|67890")
        if not exists:
            await authenticate_or_create(...)
    """
    query = """
    query CheckUserExists {
        user {
            exists
        }
    }
    """
    data = await graphql_query(query, require_auth=True)
    return data["user"]["exists"]


# Tool 3: Get User By ID (REMOVED - not supported by backend schema)
# Backend only exposes 'user { me }' for authenticated user, not arbitrary user lookup


# Tool 4: Authenticate or Create User
class AuthenticateOrCreateInput(BaseModel):
    """Input for authenticate_or_create tool."""
    auth0_sub: str = Field(description="Auth0 subject ID (e.g., 'auth0|123456')")
    email: Optional[str] = Field(None, description="User email address")
    name: Optional[str] = Field(None, description="User display name")


@mcp.tool()
async def authenticate_or_create(input: AuthenticateOrCreateInput) -> dict:
    """🚀 Authenticate existing user OR create new account on first login.
    
    ⚠️ REQUIRED for first-time login after Auth0 authentication.
    Idempotent operation - safe to call multiple times.
    
    Workflow:
    1. Check if user exists by auth0_sub
    2. If exists → Return existing profile
    3. If new → Create user with provided data
    
    Args:
        input: Authentication data
            - auth0_sub: Auth0 ID (required, e.g., "auth0|123")
            - email: Email address (optional but recommended)
            - name: Display name (optional, default: email prefix)
    
    Returns:
        User profile (new or existing):
        - id: Newly generated UUID (if new user)
        - auth0Sub, email, name: Provided data
        - language: "en" (default), theme: "auto" (default)
        - isActive: true, createdAt: Current timestamp
    
    Example:
        user = await authenticate_or_create(
            auth0_sub="auth0|123",
            email="user@example.com",
            name="John Doe"
        )
    """
    query = """
    mutation AuthenticateOrCreate {
        user {
            authenticate {
                userId
                auth0Sub
                preferences {
                    data
                }
                createdAt
                updatedAt
                lastAuthenticatedAt
                isActive
            }
        }
    }
    """
    data = await graphql_query(query, require_auth=True)
    return data["user"]["authenticate"]


# Tool 5: Update Preferences
class UpdatePreferencesInput(BaseModel):
    """Input for update_preferences tool."""
    language: Optional[str] = Field(None, description="Language ISO code (e.g., 'it', 'en')")
    theme: Optional[str] = Field(None, description="UI theme: 'light', 'dark', or 'auto'")
    notifications: Optional[bool] = Field(None, description="Enable/disable notifications")


@mcp.tool()
async def update_preferences(input: UpdatePreferencesInput) -> dict:
    """⚙️ Update user preferences and settings.
    
    Partial update operation - all fields are optional.
    Only provided fields will be updated, others remain unchanged.
    
    Args:
        input: Preferences to update (all optional)
            - language: ISO 639-1 code (e.g., "it", "en", "es")
            - theme: UI theme → "light" | "dark" | "auto"
            - notifications: Enable push notifications → true | false
    
    Returns:
        Updated user profile (partial):
        - id: User UUID (unchanged)
        - language, theme, notificationsEnabled: Updated values
        - updatedAt: New timestamp
    
    Example:
        # Update only theme
        await update_preferences(theme="dark")
        
        # Update multiple fields
        await update_preferences(
            language="it",
            theme="dark",
            notifications=True
        )
    """
    # Build preferences JSON object
    preferences_data = {}
    if input.language:
        preferences_data["language"] = input.language
    if input.theme:
        preferences_data["theme"] = input.theme
    if input.notifications is not None:
        preferences_data["notificationsEnabled"] = input.notifications
    
    query = """
    mutation UpdatePreferences($preferences: UserPreferencesInput!) {
        user {
            updatePreferences(preferences: $preferences) {
                userId
                preferences {
                    data
                }
                updatedAt
            }
        }
    }
    """
    data = await graphql_query(
        query,
        variables={"preferences": {"data": preferences_data}},
        require_auth=True
    )
    return data["user"]["updatePreferences"]


# Tool 6: Deactivate Account
@mcp.tool()
async def deactivate_account() -> dict:
    """Soft delete user account (mark as inactive).
    
    This is a destructive operation. User data is preserved but account
    is marked inactive and can no longer log in.
    
    Requires JWT token. Returns confirmation message.
    """
    query = """
    mutation DeactivateAccount {
        user {
            deactivate {
                userId
                isActive
                updatedAt
            }
        }
    }
    """
    data = await graphql_query(query, require_auth=True)
    return data["user"]["deactivate"]


if __name__ == "__main__":
    mcp.run()
