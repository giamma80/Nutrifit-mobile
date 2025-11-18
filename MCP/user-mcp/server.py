#!/usr/bin/env python3
"""
Nutrifit User MCP Server

Model Context Protocol server for the Nutrifit User domain. Provides tools
for AI assistants to help with user authentication and profile management.

IMPORTANT FOR AI ASSISTANTS:
==========================
This server provides 6 tools for user management:

🔐 AUTHENTICATION & QUERIES:
1. get_current_user() - Get authenticated user data (requires JWT)
2. check_user_exists(auth0_sub) - Verify if user exists
3. get_user_by_id(user_id) - Get user by UUID (requires JWT)

✏️ MUTATIONS:
4. authenticate_or_create(auth0_sub) - First login/create user (requires JWT)
5. update_preferences(language?, theme?, notifications?) - Update settings (requires JWT)
6. deactivate_account() - Soft delete user account (requires JWT)

CRITICAL AUTH REQUIREMENTS:
⚠️ MOST tools require JWT token in Authorization header
⚠️ Token must match the auth0_sub in the request
⚠️ Only check_user_exists is public (no JWT required)

JWT TOKEN HANDLING:
- Token should be passed via environment variable: AUTH0_TOKEN
- Format: "Bearer eyJ..."
- Token must be valid and not expired
- Backend verifies RS256 signature with Auth0 JWKS

ENUM VALUES (from GraphQL schema):
- language: ISO codes (e.g., "it", "en", "es")
- theme: "light", "dark", "auto"
- notifications: boolean

TYPICAL WORKFLOWS:
1. First login: check_user_exists → authenticate_or_create
2. Update settings: update_preferences with desired fields
3. Get profile: get_current_user
4. Delete account: deactivate_account

PARAMETER NOTES:
- auth0_sub format: "auth0|123456" or "google-oauth2|123456"
- user_id format: UUID v4
- All preferences fields are optional in update_preferences
"""

import asyncio
import json
import os
from typing import Any, Optional

import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field


# API endpoint configuration
GRAPHQL_ENDPOINT = os.getenv("GRAPHQL_ENDPOINT", "http://localhost:8080/graphql")
DEFAULT_TIMEOUT = 30.0


class GraphQLClient:
    """Client for executing GraphQL queries against Nutrifit backend."""

    def __init__(self, endpoint: str = GRAPHQL_ENDPOINT):
        self.endpoint = endpoint
        self.auth_token = os.getenv("AUTH0_TOKEN")  # Optional JWT token

    async def execute(
        self, query: str, variables: Optional[dict] = None, require_auth: bool = False
    ) -> dict:
        """Execute a GraphQL query and return the response."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        headers = {"Content-Type": "application/json"}
        if require_auth and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif require_auth and not self.auth_token:
            raise Exception(
                "AUTH0_TOKEN environment variable required for authenticated requests"
            )

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                self.endpoint, json=payload, headers=headers
            )
            response.raise_for_status()
            result = response.json()

        if "errors" in result:
            error_messages = [
                err.get("message", str(err)) for err in result["errors"]
            ]
            raise Exception(f"GraphQL errors: {'; '.join(error_messages)}")

        return result.get("data", {})


# Initialize server and client
app = Server("nutrifit-user")
gql_client = GraphQLClient()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available user management tools."""
    return [
        Tool(
            name="get_current_user",
            description="""
Get the currently authenticated user's data.

**Requires**: JWT Auth0 token (set AUTH0_TOKEN env var)

**Returns**:
- userId: UUID
- auth0Sub: Auth0 subject identifier
- createdAt: ISO timestamp
- lastAuthenticatedAt: ISO timestamp
- isActive: boolean
- preferences: { language, theme, notificationsEnabled }

**Use when**:
- User asks "who am I?"
- Need to check current user settings
- Verify authentication status

**Example**:
User: "What's my current theme?"
→ get_current_user
→ Returns: { preferences: { theme: "dark" } }
""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="check_user_exists",
            description="""
Check if a user exists given their Auth0 subject identifier.

**Public**: No authentication required

**Parameters**:
- auth0_sub (string, required): Auth0 subject (e.g., "auth0|123456")

**Returns**:
- exists: boolean
- userId: UUID (null if doesn't exist)

**Use when**:
- Onboarding flow (check before creating user)
- Verifying user registration status

**Example**:
User: "Check if user auth0|123456 exists"
→ check_user_exists(auth0_sub="auth0|123456")
→ Returns: { exists: true, userId: "uuid-here" }
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "auth0_sub": {
                        "type": "string",
                        "description": "Auth0 subject identifier (e.g., 'auth0|123456')",
                    }
                },
                "required": ["auth0_sub"],
            },
        ),
        Tool(
            name="get_user_by_id",
            description="""
Get user data by UUID.

**Requires**: JWT Auth0 token (set AUTH0_TOKEN env var)

**Parameters**:
- user_id (string, required): User UUID

**Returns**:
- userId: UUID
- auth0Sub: Auth0 subject
- createdAt: ISO timestamp
- lastAuthenticatedAt: ISO timestamp
- isActive: boolean
- preferences: { language, theme, notificationsEnabled }

**Use when**:
- Admin operations (future)
- Cross-reference user data

**Example**:
User: "Get user data for uuid-123"
→ get_user_by_id(user_id="uuid-123")
→ Returns: { userId: "uuid-123", ... }
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User UUID",
                    }
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="authenticate_or_create",
            description="""
Authenticate user or create if first login.

**Requires**: JWT Auth0 token (set AUTH0_TOKEN env var)
**Important**: Token must contain matching auth0_sub

**Parameters**:
- auth0_sub (string, required): Auth0 subject from JWT

**Returns**:
- userId: UUID
- isNewUser: boolean (true if just created)
- user: { userId, auth0Sub, createdAt, lastAuthenticatedAt, preferences }

**Behavior**:
- If user doesn't exist → creates with default preferences
- If user exists → updates lastAuthenticatedAt

**Use when**:
- First time login
- Every app launch (to update lastAuthenticatedAt)

**Example**:
User: "Authenticate me"
→ authenticate_or_create(auth0_sub="auth0|123")
→ Returns: { userId: "uuid", isNewUser: false, user: {...} }
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "auth0_sub": {
                        "type": "string",
                        "description": "Auth0 subject identifier from JWT token",
                    }
                },
                "required": ["auth0_sub"],
            },
        ),
        Tool(
            name="update_preferences",
            description="""
Update user preferences (language, theme, notifications).

**Requires**: JWT Auth0 token (set AUTH0_TOKEN env var)

**Parameters** (all optional, at least one required):
- language (string, optional): ISO language code (e.g., "it", "en")
- theme (string, optional): "light", "dark", or "auto"
- notifications_enabled (boolean, optional): Enable/disable notifications

**Returns**:
- success: boolean
- user: { userId, preferences: { ... } }

**Use when**:
- User changes app settings
- Onboarding preferences setup

**Example**:
User: "Set my theme to dark mode"
→ update_preferences(theme="dark")
→ Returns: { success: true, user: { preferences: { theme: "dark" } } }
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "ISO language code (e.g., 'it', 'en', 'es')",
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["light", "dark", "auto"],
                        "description": "UI theme preference",
                    },
                    "notifications_enabled": {
                        "type": "boolean",
                        "description": "Enable or disable notifications",
                    },
                },
                "additionalProperties": False,
            },
        ),
        Tool(
            name="deactivate_account",
            description="""
Deactivate user account (soft delete).

**Requires**: JWT Auth0 token (set AUTH0_TOKEN env var)

**Parameters**: None (deactivates authenticated user)

**Returns**:
- success: boolean
- userId: UUID of deactivated user

**Behavior**:
- Sets isActive = false
- Does NOT delete data (GDPR compliance)
- User can reactivate by logging in again

**Use when**:
- User requests account deletion
- Temporary account suspension

**Example**:
User: "Delete my account"
→ deactivate_account()
→ Returns: { success: true, userId: "uuid" }
""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution."""
    try:
        if name == "get_current_user":
            result = await get_current_user()
        elif name == "check_user_exists":
            result = await check_user_exists(arguments["auth0_sub"])
        elif name == "get_user_by_id":
            result = await get_user_by_id(arguments["user_id"])
        elif name == "authenticate_or_create":
            result = await authenticate_or_create(arguments["auth0_sub"])
        elif name == "update_preferences":
            result = await update_preferences(
                language=arguments.get("language"),
                theme=arguments.get("theme"),
                notifications_enabled=arguments.get("notifications_enabled"),
            )
        elif name == "deactivate_account":
            result = await deactivate_account()
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_response = {"error": str(e), "tool": name, "arguments": arguments}
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


# Tool implementations
async def get_current_user() -> dict:
    """Get currently authenticated user."""
    query = """
    query GetCurrentUser {
      user {
        me {
          userId
          auth0Sub
          createdAt
          lastAuthenticatedAt
          isActive
          preferences {
            language
            theme
            notificationsEnabled
          }
        }
      }
    }
    """
    data = await gql_client.execute(query, require_auth=True)
    return data.get("user", {}).get("me", {})


async def check_user_exists(auth0_sub: str) -> dict:
    """Check if user exists."""
    query = """
    query CheckUserExists($auth0Sub: String!) {
      user {
        exists(auth0Sub: $auth0Sub) {
          exists
          userId
        }
      }
    }
    """
    variables = {"auth0Sub": auth0_sub}
    data = await gql_client.execute(query, variables)
    return data.get("user", {}).get("exists", {})


async def get_user_by_id(user_id: str) -> dict:
    """Get user by ID."""
    query = """
    query GetUserById($userId: String!) {
      user {
        byId(userId: $userId) {
          userId
          auth0Sub
          createdAt
          lastAuthenticatedAt
          isActive
          preferences {
            language
            theme
            notificationsEnabled
          }
        }
      }
    }
    """
    variables = {"userId": user_id}
    data = await gql_client.execute(query, variables, require_auth=True)
    return data.get("user", {}).get("byId", {})


async def authenticate_or_create(auth0_sub: str) -> dict:
    """Authenticate or create user."""
    mutation = """
    mutation AuthenticateOrCreate($auth0Sub: String!) {
      user {
        authenticateOrCreate(input: { auth0Sub: $auth0Sub }) {
          userId
          isNewUser
          user {
            userId
            auth0Sub
            createdAt
            lastAuthenticatedAt
            isActive
            preferences {
              language
              theme
              notificationsEnabled
            }
          }
        }
      }
    }
    """
    variables = {"auth0Sub": auth0_sub}
    data = await gql_client.execute(mutation, variables, require_auth=True)
    return data.get("user", {}).get("authenticateOrCreate", {})


async def update_preferences(
    language: Optional[str] = None,
    theme: Optional[str] = None,
    notifications_enabled: Optional[bool] = None,
) -> dict:
    """Update user preferences."""
    # Build input object with only provided fields
    input_obj = {}
    if language is not None:
        input_obj["language"] = language
    if theme is not None:
        input_obj["theme"] = theme
    if notifications_enabled is not None:
        input_obj["notificationsEnabled"] = notifications_enabled

    if not input_obj:
        raise ValueError("At least one preference field must be provided")

    mutation = """
    mutation UpdatePreferences($input: UserPreferencesInput!) {
      user {
        updatePreferences(input: $input) {
          success
          user {
            userId
            preferences {
              language
              theme
              notificationsEnabled
            }
          }
        }
      }
    }
    """
    variables = {"input": input_obj}
    data = await gql_client.execute(mutation, variables, require_auth=True)
    return data.get("user", {}).get("updatePreferences", {})


async def deactivate_account() -> dict:
    """Deactivate user account."""
    mutation = """
    mutation DeactivateAccount {
      user {
        deactivate {
          success
          userId
        }
      }
    }
    """
    data = await gql_client.execute(mutation, require_auth=True)
    return data.get("user", {}).get("deactivate", {})


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
