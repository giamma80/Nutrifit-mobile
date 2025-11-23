#!/usr/bin/env python3
"""
Test script per verificare integrazione MCP completa.

Verifica:
1. Tutti i tools sono disponibili
2. Le firme Pydantic sono lette correttamente
3. Le descrizioni complete sono presenti
"""

import asyncio
import httpx
from typing import Dict, List

# Server URLs
SERVERS = {
    "user": "http://localhost:8004",
    "meal": "http://localhost:8001",
    "activity": "http://localhost:8002",
    "nutritional_profile": "http://localhost:8003",
}

# Expected tool counts
EXPECTED_COUNTS = {
    "user": 5,
    "meal": 15,
    "activity": 5,
    "nutritional_profile": 6,
}


async def check_server(name: str, url: str, expected_count: int) -> Dict:
    """Check server health and tools."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Health check
        try:
            health_resp = await client.get(f"{url}/health")
            health_data = health_resp.json()
        except Exception as e:
            return {
                "name": name,
                "status": "❌ UNREACHABLE",
                "error": str(e),
                "tools": 0,
                "expected": expected_count,
            }
        
        # Get tools
        try:
            tools_resp = await client.get(f"{url}/tools")
            tools = tools_resp.json()
            
            # Check completeness
            has_descriptions = all(len(t.get("description", "")) > 50 for t in tools)
            has_parameters = all("parameters" in t for t in tools)
            
            # Sample tool for inspection
            sample_tool = tools[0] if tools else None
            
            return {
                "name": name,
                "status": "✅ HEALTHY" if len(tools) == expected_count else "⚠️ MISMATCH",
                "tools_count": len(tools),
                "expected": expected_count,
                "has_full_descriptions": has_descriptions,
                "has_parameters": has_parameters,
                "sample_tool": sample_tool["name"] if sample_tool else None,
                "sample_desc_length": len(sample_tool.get("description", "")) if sample_tool else 0,
            }
        except Exception as e:
            return {
                "name": name,
                "status": "❌ ERROR",
                "error": str(e),
                "tools": 0,
                "expected": expected_count,
            }


async def main():
    print("🧪 MCP Integration Test")
    print("=" * 60)
    
    results = []
    for name, url in SERVERS.items():
        expected = EXPECTED_COUNTS[name]
        print(f"\n📡 Testing {name}-mcp ({url})...")
        result = await check_server(name, url, expected)
        results.append(result)
        
        # Print result
        print(f"  Status: {result['status']}")
        print(f"  Tools: {result.get('tools_count', 0)}/{result['expected']}")
        
        if "error" in result:
            print(f"  Error: {result['error']}")
        else:
            print(f"  Full descriptions: {'✅' if result.get('has_full_descriptions') else '❌'}")
            print(f"  Parameters: {'✅' if result.get('has_parameters') else '❌'}")
            if result.get('sample_tool'):
                print(f"  Sample: {result['sample_tool']} ({result.get('sample_desc_length')} chars)")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    total_tools = sum(r.get('tools_count', 0) for r in results)
    total_expected = sum(r['expected'] for r in results)
    all_healthy = all(r['status'].startswith("✅") for r in results)
    
    print(f"Total tools: {total_tools}/{total_expected}")
    print(f"All servers: {'✅ HEALTHY' if all_healthy else '❌ ISSUES'}")
    
    if total_tools == total_expected:
        print("\n✅ All 31 tools integrated correctly!")
    else:
        print(f"\n❌ Missing {total_expected - total_tools} tools")


if __name__ == "__main__":
    asyncio.run(main())
