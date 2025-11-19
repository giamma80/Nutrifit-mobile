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
    """Get authenticated user profile with preferences and settings.
    
    Requires JWT token in AUTH0_TOKEN environment variable.
    Returns complete user profile including preferences.
    """
    query = """
    query GetCurrentUser {
        user {
            id
            auth0Sub
            email
            name
            language
            theme
            notificationsEnabled
            isActive
            createdAt
            updatedAt
        }
    }
    """
    data = await graphql_query(query, require_auth=True)
    return data["user"]


# Tool 2: Check User Exists
@mcp.tool()
async def check_user_exists(auth0_sub: str) -> bool:
    """Check if user exists by Auth0 ID.
    
    Args:
        auth0_sub: Auth0 subject identifier (e.g., "auth0|123456")
    
    Returns:
        True if user exists, False otherwise
    """
    query = """
    query CheckUserExists($auth0Sub: String!) {
        checkUserExists(auth0Sub: $auth0Sub)
    }
    """
    data = await graphql_query(query, variables={"auth0Sub": auth0_sub})
    return data["checkUserExists"]


# Tool 3: Get User By ID
@mcp.tool()
async def get_user_by_id(user_id: str) -> dict:
    """Get user profile by UUID.
    
    Args:
        user_id: User UUID (e.g., "550e8400-e29b-41d4-a716-446655440000")
    
    Requires JWT token. Returns full user profile.
    """
    query = """
    query GetUserById($userId: ID!) {
        getUserById(id: $userId) {
            id
            auth0Sub
            email
            name
            language
            theme
            notificationsEnabled
            isActive
            createdAt
            updatedAt
        }
    }
    """
    data = await graphql_query(
        query,
        variables={"userId": user_id},
        require_auth=True
    )
    return data["getUserById"]


# Tool 4: Authenticate or Create User
class AuthenticateOrCreateInput(BaseModel):
    """Input for authenticate_or_create tool."""
    auth0_sub: str = Field(description="Auth0 subject ID (e.g., 'auth0|123456')")
    email: Optional[str] = Field(None, description="User email address")
    name: Optional[str] = Field(None, description="User display name")


@mcp.tool()
async def authenticate_or_create(input: AuthenticateOrCreateInput) -> dict:
    """Authenticate existing user or create new account on first login.
    
    Use this for first-time login after Auth0 authentication.
    If user exists, returns existing profile. Otherwise creates new user.
    
    Args:
        input: Authentication data with auth0_sub, email, name
    
    Returns:
        User profile (new or existing)
    """
    query = """
    mutation AuthenticateOrCreate($auth0Sub: String!, $email: String, $name: String) {
        authenticateOrCreateUser(auth0Sub: $auth0Sub, email: $email, name: $name) {
            id
            auth0Sub
            email
            name
            language
            theme
            notificationsEnabled
            isActive
            createdAt
            updatedAt
        }
    }
    """
    data = await graphql_query(
        query,
        variables={
            "auth0Sub": input.auth0_sub,
            "email": input.email,
            "name": input.name
        },
        require_auth=True
    )
    return data["authenticateOrCreateUser"]


# Tool 5: Update Preferences
class UpdatePreferencesInput(BaseModel):
    """Input for update_preferences tool."""
    language: Optional[str] = Field(None, description="Language ISO code (e.g., 'it', 'en')")
    theme: Optional[str] = Field(None, description="UI theme: 'light', 'dark', or 'auto'")
    notifications: Optional[bool] = Field(None, description="Enable/disable notifications")


@mcp.tool()
async def update_preferences(input: UpdatePreferencesInput) -> dict:
    """Update user preferences and settings.
    
    All fields are optional - only provided fields will be updated.
    
    Args:
        input: Preferences to update (language, theme, notifications)
    
    Returns:
        Updated user profile
    """
    query = """
    mutation UpdatePreferences($language: String, $theme: String, $notifications: Boolean) {
        updateUserPreferences(
            language: $language
            theme: $theme
            notificationsEnabled: $notifications
        ) {
            id
            language
            theme
            notificationsEnabled
            updatedAt
        }
    }
    """
    variables = {}
    if input.language:
        variables["language"] = input.language
    if input.theme:
        variables["theme"] = input.theme
    if input.notifications is not None:
        variables["notifications"] = input.notifications
    
    data = await graphql_query(query, variables=variables, require_auth=True)
    return data["updateUserPreferences"]


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
        deactivateAccount {
            id
            isActive
            updatedAt
        }
    }
    """
    data = await graphql_query(query, require_auth=True)
    return data["deactivateAccount"]


if __name__ == "__main__":
    mcp.run()
