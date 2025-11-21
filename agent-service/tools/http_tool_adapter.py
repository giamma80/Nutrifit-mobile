"""HTTP-based GraphQL tool adapter for Strands agents."""
from strands import tool
import httpx
from typing import Optional, Callable, Dict, Any


def create_graphql_tool(
    name: str,
    description: str,
    query: str,
    graphql_endpoint: str,
    auth_token: str,
    variables_mapper: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
):
    """
    Create a Strands tool that executes GraphQL queries via HTTP.
    
    Args:
        name: Tool name (unique identifier)
        description: Tool description for LLM
        query: GraphQL query/mutation string
        graphql_endpoint: Backend GraphQL endpoint URL
        auth_token: JWT Bearer token
        variables_mapper: Optional function to map tool params to GraphQL variables
    
    Returns:
        Async tool function decorated with @strands.tool
    """
    
    @tool(name=name, description=description)
    async def tool_fn(**params):
        print(f"🔧 Executing tool '{name}' with params: {params}")
        
        # Map parameters to GraphQL variables
        variables = variables_mapper(params) if variables_mapper else {}
        print(f"📊 GraphQL variables: {variables}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    graphql_endpoint,
                    json={"query": query, "variables": variables},
                    headers={
                        "Authorization": f"Bearer {auth_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                print(f"📡 GraphQL response status: {response.status_code}")
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    errors = data["errors"]
                    print(f"❌ GraphQL errors in '{name}': {errors}")
                    raise Exception(f"GraphQL errors in '{name}': {errors}")
                
                print(f"✅ Tool '{name}' succeeded")
                return data.get("data")
                
            except httpx.HTTPError as e:
                print(f"❌ HTTP error in '{name}': {e}")
                raise Exception(f"HTTP error in '{name}': {e}")
            except Exception as e:
                print(f"❌ Unexpected error in '{name}': {e}")
                raise
    
    return tool_fn
