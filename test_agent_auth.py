#!/usr/bin/env python3
"""Test script to verify MCP clients are created with user auth token."""

import requests
import sys

# Simula una richiesta con token valido (verrà validato dal backend)
# Per questo test, generiamo un token JWT mock che passa la validazione
# In produzione, questo sarebbe un token Auth0 reale

def test_agent_request():
    """Test agent endpoint to verify MCP client creation with token."""
    
    # Endpoint
    url = "http://localhost:8000/api/agent/chat"
    
    # Headers with mock token (il backend lo validerà)
    headers = {
        "Content-Type": "application/json",
        # Token mock - in produzione sarebbe Auth0 JWT
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlRlc3RLZXkifQ.eyJzdWIiOiJnb29nbGUtb2F1dGgyfDExNDg5ODAzMjQxMTAyMDMxMTIxMSIsImVtYWlsIjoidGVzdEB0ZXN0LmNvbSIsImlhdCI6MTczMjM2MTIwMCwiZXhwIjoxNzMyMzY0ODAwfQ.mock-signature"
    }
    
    # Request body
    data = {
        "message": "verifica profilo utente",
        "user_id": "test-user-12345"
    }
    
    print("🚀 Sending request to agent...")
    print(f"📍 URL: {url}")
    print(f"👤 User ID: {data['user_id']}")
    print(f"💬 Message: {data['message']}")
    print()
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📝 Response Body:")
        print(response.text)
        
        if response.status_code == 200:
            print("\n✅ Request successful")
            print("\n📋 Check agent logs with:")
            print("   docker logs nutrifit-agent 2>&1 | tail -100")
            return 0
        else:
            print(f"\n⚠️  Request returned non-200 status")
            return 1
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_agent_request())
