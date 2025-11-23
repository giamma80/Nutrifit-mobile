#!/bin/bash
# Test HTTP MCP servers locally

set -e

echo "🧪 Testing HTTP MCP Servers"
echo "=============================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test server endpoint
test_server() {
    local name=$1
    local port=$2
    
    echo ""
    echo "Testing $name on port $port..."
    
    # Health check
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health check passed${NC}"
    else
        echo -e "${RED}❌ Health check failed${NC}"
        return 1
    fi
    
    # List tools
    tools=$(curl -s "http://localhost:$port/tools" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
    echo -e "${GREEN}✅ Found $tools tools${NC}"
}

# Test meal server
if [ -f "../MCP/meal-mcp/server_http.py" ]; then
    echo "Starting meal-mcp server..."
    cd ../MCP/meal-mcp
    PORT=8001 python server_http.py &
    MEAL_PID=$!
    sleep 2
    test_server "meal-mcp" 8001
    kill $MEAL_PID 2>/dev/null || true
fi

# Test activity server
if [ -f "../MCP/activity-mcp/server_http.py" ]; then
    echo "Starting activity-mcp server..."
    cd ../MCP/activity-mcp
    PORT=8002 python server_http.py &
    ACTIVITY_PID=$!
    sleep 2
    test_server "activity-mcp" 8002
    kill $ACTIVITY_PID 2>/dev/null || true
fi

# Test nutritional-profile server
if [ -f "../MCP/nutritional-profile-mcp/server_http.py" ]; then
    echo "Starting nutritional-profile-mcp server..."
    cd ../MCP/nutritional-profile-mcp
    PORT=8003 python server_http.py &
    PROFILE_PID=$!
    sleep 2
    test_server "nutritional-profile-mcp" 8003
    kill $PROFILE_PID 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}✅ All tests passed${NC}"
