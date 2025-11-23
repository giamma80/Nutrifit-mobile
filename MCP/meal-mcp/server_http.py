#!/usr/bin/env python3
"""
Nutrifit Meal MCP Server - HTTP Mode

HTTP server che espone i tools FastMCP come REST API endpoints.
Risolve il problema di blocking STDIO handshake usando HTTP transport.
"""

import inspect
import os
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import FastMCP server con tutti i tools
from server_fastmcp import (
    mcp,
    upload_meal_image,
    search_food_by_barcode,
    recognize_food,
    enrich_nutrients,
    analyze_meal_photo,
    analyze_meal_text,
    analyze_meal_barcode,
    confirm_meal_analysis,
    get_meal,
    get_meal_history,
    search_meals,
    get_daily_summary,
    get_summary_range,
    update_meal,
    delete_meal,
)


# Configuration
PORT = int(os.getenv("PORT", "8001"))
HOST = os.getenv("HOST", "0.0.0.0")


# FastAPI app
app = FastAPI(
    title="Nutrifit Meal MCP Server",
    description="HTTP MCP server for meal tracking and nutrition analysis",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ToolCallRequest(BaseModel):
    """Request body per chiamata tool."""
    arguments: Dict[str, Any]


class ToolCallResponse(BaseModel):
    """Response di chiamata tool."""
    result: Any
    error: str | None = None


class ToolInfo(BaseModel):
    """Informazioni su un tool."""
    name: str
    description: str
    parameters: Dict[str, Any]


# Tool registry - mappa nome → funzione
TOOL_REGISTRY = {
    "upload_meal_image": upload_meal_image,
    "search_food_by_barcode": search_food_by_barcode,
    "recognize_food": recognize_food,
    "enrich_nutrients": enrich_nutrients,
    "analyze_meal_photo": analyze_meal_photo,
    "analyze_meal_text": analyze_meal_text,
    "analyze_meal_barcode": analyze_meal_barcode,
    "confirm_meal_analysis": confirm_meal_analysis,
    "get_meal": get_meal,
    "get_meal_history": get_meal_history,
    "search_meals": search_meals,
    "get_daily_summary": get_daily_summary,
    "get_summary_range": get_summary_range,
    "update_meal": update_meal,
    "delete_meal": delete_meal,
}


def get_auth_token(authorization: str = Header(None)) -> str:
    """Extract and validate auth token from header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    # Remove 'Bearer ' prefix if present
    token = authorization.replace("Bearer ", "")
    return token


def extract_tool_schema(func) -> Dict[str, Any]:
    """Extract parameter schema from function signature with Pydantic support."""
    sig = inspect.signature(func)
    parameters = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        if param_name in ["self", "cls"]:
            continue
        
        param_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
        
        # Check if it's a Pydantic BaseModel
        try:
            if hasattr(param_type, "model_json_schema"):
                # It's a Pydantic model - extract its schema
                pydantic_schema = param_type.model_json_schema()
                # Flatten nested schema for input parameter
                if "properties" in pydantic_schema:
                    parameters.update(pydantic_schema["properties"])
                    if "required" in pydantic_schema:
                        required.extend(pydantic_schema["required"])
                continue
        except:
            pass
        
        # Simple type mapping
        type_str = "string"
        if param_type == int:
            type_str = "integer"
        elif param_type == float:
            type_str = "number"
        elif param_type == bool:
            type_str = "boolean"
        elif param_type == list or param_type == List:
            type_str = "array"
        elif param_type == dict or param_type == Dict:
            type_str = "object"
        elif param_type == str:
            type_str = "string"
        
        parameters[param_name] = {"type": type_str}
        
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
    
    schema = {
        "type": "object",
        "properties": parameters,
    }
    
    if required:
        schema["required"] = required
    
    return schema


# === ENDPOINTS ===

@app.get("/")
async def root():
    """Health check."""
    return {
        "service": "nutrifit-meal-mcp",
        "status": "healthy",
        "version": "1.0.0",
        "transport": "http",
        "tools": len(TOOL_REGISTRY),
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "tools_available": list(TOOL_REGISTRY.keys()),
        "tools_count": len(TOOL_REGISTRY),
    }


@app.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """List all available tools with their schemas."""
    tools = []
    
    for name, func in TOOL_REGISTRY.items():
        # Extract docstring
        doc = inspect.getdoc(func) or "No description"
        
        # Extract parameter schema
        schema = extract_tool_schema(func)
        
        tools.append(ToolInfo(
            name=name,
            description=doc,
            parameters=schema,
        ))
    
    return tools


@app.post("/tools/{tool_name}", response_model=ToolCallResponse)
async def call_tool(
    tool_name: str,
    request: ToolCallRequest,
    auth_token: str = Depends(get_auth_token),
):
    """Execute a tool with provided arguments."""
    
    # Check if tool exists
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. Available: {list(TOOL_REGISTRY.keys())}"
        )
    
    # Get tool function
    tool_func = TOOL_REGISTRY[tool_name]
    
    try:
        # Inject auth_token se la funzione lo richiede
        args = request.arguments.copy()
        
        # Check if function accepts auth_token parameter
        sig = inspect.signature(tool_func)
        if "auth_token" in sig.parameters:
            args["auth_token"] = auth_token
        
        # Call tool
        result = await tool_func(**args)
        
        return ToolCallResponse(result=result, error=None)
    
    except TypeError as e:
        # Parameter mismatch
        raise HTTPException(
            status_code=400,
            detail=f"Invalid arguments for tool '{tool_name}': {str(e)}"
        )
    
    except Exception as e:
        # Tool execution error
        return ToolCallResponse(
            result=None,
            error=f"Tool execution failed: {str(e)}"
        )


# === STARTUP ===

if __name__ == "__main__":
    print(f"🚀 Starting Nutrifit Meal MCP Server (HTTP)")
    print(f"📍 Listening on {HOST}:{PORT}")
    print(f"🔧 {len(TOOL_REGISTRY)} tools available")
    print(f"📋 Tools: {', '.join(TOOL_REGISTRY.keys())}")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )
