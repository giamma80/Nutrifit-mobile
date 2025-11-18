# Nutrifit User MCP Server

Model Context Protocol server for the **Nutrifit User Domain**. Provides authentication and profile management tools for AI assistants.

## 🎯 Purpose

Enable AI assistants (Claude, GPT, etc.) to help users with:

- **Authentication**: Login, registration, session management
- **Profile Management**: User preferences, account settings
- **Account Operations**: Deactivation, reactivation

## 📦 Tools (6 total)

### 🔐 Authentication & Queries

#### 1. `get_current_user()`

Get the currently authenticated user's complete profile.

**Requires**: JWT Auth0 token (set `AUTH0_TOKEN` env var)

**Returns**:

```json
{
  "userId": "uuid-v4",
  "auth0Sub": "auth0|123456",
  "createdAt": "2025-11-18T10:00:00Z",
  "lastAuthenticatedAt": "2025-11-18T15:30:00Z",
  "isActive": true,
  "preferences": {
    "language": "it",
    "theme": "dark",
    "notificationsEnabled": true
  }
}
```

**Example usage**:

```
User: "What's my current theme?"
→ get_current_user()
→ AI extracts: theme = "dark"
```

---

#### 2. `check_user_exists(auth0_sub)`

Verify if a user exists in the database.

**Public**: No authentication required

**Parameters**:

- `auth0_sub` (string): Auth0 subject identifier (e.g., `"auth0|123456"`)

**Returns**:

```json
{
  "exists": true,
  "userId": "uuid-v4"  // null if doesn't exist
}
```

**Example usage**:

```
Onboarding: "Check if user auth0|123 is registered"
→ check_user_exists(auth0_sub="auth0|123")
→ Returns: { exists: false, userId: null }
→ AI suggests: "User not registered, create account?"
```

---

#### 3. `get_user_by_id(user_id)`

Retrieve user data by UUID.

**Requires**: JWT Auth0 token

**Parameters**:

- `user_id` (string): User UUID

**Returns**: Same structure as `get_current_user()`

**Example usage**:

```
Admin: "Show me user uuid-123's settings"
→ get_user_by_id(user_id="uuid-123")
```

---

### ✏️ Mutations

#### 4. `authenticate_or_create(auth0_sub)`

Authenticate user or create if first login.

**Requires**: JWT Auth0 token (token must match `auth0_sub`)

**Parameters**:

- `auth0_sub` (string): Auth0 subject from JWT token

**Returns**:

```json
{
  "userId": "uuid-v4",
  "isNewUser": false,  // true if just created
  "user": {
    "userId": "uuid-v4",
    "auth0Sub": "auth0|123456",
    ...
  }
}
```

**Behavior**:

- **If user doesn't exist**: Creates with default preferences (`language: "en"`, `theme: "light"`, `notificationsEnabled: true`)
- **If user exists**: Updates `lastAuthenticatedAt` timestamp

**Example usage**:

```
App launch: "Authenticate me"
→ authenticate_or_create(auth0_sub="auth0|123")
→ If isNewUser=true: "Welcome! Setup your profile"
→ If isNewUser=false: "Welcome back!"
```

---

#### 5. `update_preferences(language?, theme?, notifications_enabled?)`

Update user preferences (all fields optional, at least one required).

**Requires**: JWT Auth0 token

**Parameters**:

- `language` (string, optional): ISO code (`"it"`, `"en"`, `"es"`)
- `theme` (string, optional): `"light"`, `"dark"`, `"auto"`
- `notifications_enabled` (boolean, optional): Enable/disable notifications

**Returns**:

```json
{
  "success": true,
  "user": {
    "userId": "uuid-v4",
    "preferences": {
      "language": "it",
      "theme": "dark",
      "notificationsEnabled": true
    }
  }
}
```

**Example usage**:

```
User: "Change my language to Italian"
→ update_preferences(language="it")
→ Returns: { success: true, ... }
→ AI confirms: "Language updated to Italian ✅"
```

---

#### 6. `deactivate_account()`

Deactivate user account (soft delete).

**Requires**: JWT Auth0 token

**Parameters**: None (deactivates authenticated user)

**Returns**:

```json
{
  "success": true,
  "userId": "uuid-v4"
}
```

**Behavior**:

- Sets `isActive = false`
- **Does NOT delete data** (GDPR compliance)
- User can reactivate by logging in again

**Example usage**:

```
User: "Delete my account"
→ deactivate_account()
→ Returns: { success: true }
→ AI warns: "Account deactivated. Login again to reactivate."
```

---

## 🚀 Installation

**Option 1: Use shared MCP venv** (recommended)

```bash
cd /Users/giamma/workspace/Nutrifit-mobile/MCP
source .venv/bin/activate  # Shared venv for all MCP servers
```

**Option 2: Create dedicated venv**

```bash
cd user-mcp
uv venv
uv pip install mcp httpx pydantic
```

## ⚙️ Configuration

### Environment Variables

- `GRAPHQL_ENDPOINT`: Backend GraphQL URL (default: `http://localhost:8080/graphql`)
- `AUTH0_TOKEN`: JWT token for authenticated requests (optional, but required for most tools)

### Claude Desktop Setup

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nutrifit-user": {
      "command": "/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python",
      "args": [
        "/Users/giamma/workspace/Nutrifit-mobile/MCP/user-mcp/server.py"
      ],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql",
        "AUTH0_TOKEN": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
      }
    }
  }
}
```

**⚠️ Important**: Use absolute paths and restart Claude Desktop after changes.

## 🔐 Authentication

### JWT Token Requirement

Most tools (except `check_user_exists`) require a valid Auth0 JWT token.

**Token format**:

```
Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhdXRoMHwxMjM0NTYiLCJhdWQiOiJodHRwczovL2FwaS5udXRyaWZpdC5hcHAiLCJleHAiOjE3MzIwMDAwMDB9...
```

**Token must contain**:

- `sub`: Auth0 subject matching the user
- `aud`: `https://api.nutrifit.app`
- `exp`: Not expired

### Getting a Token

**For testing**:

```bash
# Get M2M token from Auth0
curl --request POST \
  --url https://YOUR-TENANT.auth0.com/oauth/token \
  --data '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://api.nutrifit.app",
    "grant_type": "client_credentials"
  }'
```

**For production**: Users obtain tokens via Auth0 Universal Login in the mobile/web app.

## 💡 Usage Patterns

### First Login Flow

```
1. User logs in with Auth0 (mobile app handles this)
2. App receives JWT token
3. AI calls: authenticate_or_create(auth0_sub)
4. If isNewUser=true → show onboarding
5. If isNewUser=false → show dashboard
```

### Preferences Update Flow

```
1. User: "Set dark mode"
2. AI calls: update_preferences(theme="dark")
3. AI confirms: "Theme updated to dark ✅"
```

### Account Deletion Flow

```
1. User: "Delete my account"
2. AI warns: "This will deactivate your account. Continue?"
3. User confirms
4. AI calls: deactivate_account()
5. AI confirms: "Account deactivated. Login to reactivate."
```

## 🧪 Testing

**Test without authentication** (check_user_exists only):

```bash
# Start backend
cd backend && make run

# In another terminal
cd MCP/user-mcp
python server.py
```

Then in Claude Desktop:

```
"Check if user auth0|test exists"
```

**Test with authentication** (requires token):

1. Get test token from Auth0
2. Set in `claude_desktop_config.json` → `env.AUTH0_TOKEN`
3. Restart Claude Desktop
4. Test: "What's my current theme?"

## 🐛 Troubleshooting

### "AUTH0_TOKEN environment variable required"

**Cause**: Tool requires JWT but token not set

**Solution**:

1. Get token from Auth0 (see Authentication section)
2. Add to Claude config: `env.AUTH0_TOKEN = "Bearer ..."`
3. Restart Claude Desktop

### "GraphQL errors: MISSING_AUTHENTICATION"

**Cause**: Token missing or invalid

**Solution**:

1. Verify token not expired
2. Check token format: `Bearer eyJ...`
3. Verify token matches user's `auth0_sub`

### "User not found"

**Cause**: User doesn't exist in database

**Solution**:

1. Call `check_user_exists(auth0_sub)` first
2. If doesn't exist, call `authenticate_or_create(auth0_sub)`

## 📚 API Reference

See complete GraphQL schema in:

**`/backend/REFACTOR/graphql-api-reference.md`** → Section "Namespace: User"

## 🔗 Related MCP Servers

- **meal-mcp**: Meal tracking and nutrition analysis
- **activity-mcp**: Activity tracking and health data
- **nutritional-profile-mcp**: Profile management and progress

## 📝 License

See root LICENSE file.

---

**Built with ❤️ for Nutrifit**
