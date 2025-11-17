#!/bin/bash
set -e

# Nutrifit Auth0 Integration Test
# Usage: ./test_auth0.sh [access_token]
# If no token provided, will fetch one using client credentials

ENDPOINT="${ENDPOINT:-http://localhost:8000}"
AUTH0_DOMAIN="${AUTH0_DOMAIN:-dev-1grp81dl273fd86f.us.auth0.com}"
CLIENT_ID="${CLIENT_ID:-4Po4EMtD5sQn4pu86u3eNzLg31FICnS4}"
CLIENT_SECRET="${CLIENT_SECRET:-s9vQGv8tCuHdi9OPb3I1PmW1v7_0m_LQbBa0CXevMKtNl6pxL4eZUeEhe9i23bD_}"
AUDIENCE="${AUDIENCE:-https://api.nutrifit.app}"

# Get token from argument or fetch new one
if [ -n "$1" ]; then
  TOKEN="$1"
  echo "📝 Using provided token"
else
  echo "🔑 Fetching access token from Auth0..."
  TOKEN_RESPONSE=$(curl -s --request POST \
    --url "https://${AUTH0_DOMAIN}/oauth/token" \
    --header 'content-type: application/json' \
    --data "{
      \"client_id\":\"${CLIENT_ID}\",
      \"client_secret\":\"${CLIENT_SECRET}\",
      \"audience\":\"${AUDIENCE}\",
      \"grant_type\":\"client_credentials\"
    }")
  
  TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
  
  if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Failed to get access token"
    echo "$TOKEN_RESPONSE" | jq '.'
    exit 1
  fi
  echo "✅ Token obtained successfully"
fi

echo "=== Auth0 Integration Test ==="
echo "Endpoint: $ENDPOINT"
echo "Token: ${TOKEN:0:50}..."
echo ""

# Test 1: Mutation authenticate (creates user if doesn't exist)
echo "🔄 Test 1: Mutation authenticate"
RESPONSE=$(curl -s "$ENDPOINT/graphql" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"mutation { user { authenticate { userId auth0Sub lastAuthenticatedAt isActive } } }"}')

echo "$RESPONSE" | jq '.'

if echo "$RESPONSE" | jq -e '.data.user.authenticate.userId' > /dev/null; then
  echo "✅ authenticate successful"
  USER_ID=$(echo "$RESPONSE" | jq -r '.data.user.authenticate.userId')
  echo "   User ID: $USER_ID"
else
  echo "❌ Mutation failed"
  echo "$RESPONSE" | jq '.errors'
  exit 1
fi

# Test 2: Query user.me (should return user data now)
echo ""
echo "🔐 Test 2: Query user.me (authenticated)"
RESPONSE=$(curl -s "$ENDPOINT/graphql" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"{ user { me { userId auth0Sub createdAt isActive } } }"}')

echo "$RESPONSE" | jq '.'

if echo "$RESPONSE" | jq -e '.data.user.me.userId' > /dev/null; then
  echo "✅ Query user.me successful"
else
  echo "❌ Query failed"
  echo "$RESPONSE" | jq '.errors'
  exit 1
fi

# Test 3: Update preferences
echo ""
echo "⚙️  Test 3: Update user preferences"
RESPONSE=$(curl -s "$ENDPOINT/graphql" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"query\":\"mutation { user { updatePreferences(preferences: { data: { language: \\\"it\\\", theme: \\\"dark\\\", notifications: true } }) { userId preferences { data } } } }\"}")

echo "$RESPONSE" | jq '.'

if echo "$RESPONSE" | jq -e '.data.user.updatePreferences.userId' > /dev/null; then
  echo "✅ Preferences updated"
else
  echo "❌ Update failed"
fi

echo ""
echo "=== All Auth0 tests completed ==="
