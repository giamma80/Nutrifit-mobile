#!/usr/bin/env python3
"""
Nutrifit Nutritional Profile MCP Server - HTTP Mode

HTTP server che espone i tools FastMCP come REST API endpoints.
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
    get_nutritional_profile,
    create_nutritional_profile,
    update_nutritional_profile,
    record_progress,
    get_progress_score,
    forecast_weight,
)


# Configuration
PORT = int(os.getenv("PORT", "8003"))
HOST = os.getenv("HOST", "0.0.0.0")


# FastAPI app
app = FastAPI(
    title="Nutrifit Nutritional Profile MCP Server",
    description="HTTP MCP server for profile management and progress tracking",
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


# Tool registry
TOOL_REGISTRY = {
    "get_nutritional_profile": get_nutritional_profile,
    "create_nutritional_profile": create_nutritional_profile,
    "update_nutritional_profile": update_nutritional_profile,
    "record_progress": record_progress,
    "get_progress_score": get_progress_score,
    "forecast_weight": forecast_weight,
}


def get_auth_token(authorization: str = Header(None)) -> str:
    """Extract and validate auth token from header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
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
                pydantic_schema = param_type.model_json_schema()
                if "properties" in pydantic_schema:
                    parameters.update(pydantic_schema["properties"])
                    if "required" in pydantic_schema:
                        required.extend(pydantic_schema["required"])
                continue
        except:
            pass
        
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
        "service": "nutrifit-nutritional-profile-mcp",
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
        doc = inspect.getdoc(func) or "No description"
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
    
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. Available: {list(TOOL_REGISTRY.keys())}"
        )
    
    tool_func = TOOL_REGISTRY[tool_name]
    
    try:
        args = request.arguments.copy()
        
        sig = inspect.signature(tool_func)
        if "auth_token" in sig.parameters:
            args["auth_token"] = auth_token
        
        result = await tool_func(**args)
        
        return ToolCallResponse(result=result, error=None)
    
    except TypeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid arguments for tool '{tool_name}': {str(e)}"
        )
    
    except Exception as e:
        return ToolCallResponse(
            result=None,
            error=f"Tool execution failed: {str(e)}"
        )


# === STARTUP ===

if __name__ == "__main__":
    print(f"🚀 Starting Nutrifit Nutritional Profile MCP Server (HTTP)")
    print(f"📍 Listening on {HOST}:{PORT}")
    print(f"🔧 {len(TOOL_REGISTRY)} tools available")
    print(f"📋 Tools: {', '.join(TOOL_REGISTRY.keys())}")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )
