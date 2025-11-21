"""FastAPI application for Nutrifit Agent Service.

This service provides an AI agent interface powered by Strands and MCP servers.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import redis.asyncio as redis

from auth.middleware import get_current_user
from agents.nutrifit_agent import agent_manager


# Redis client (optional)
redis_client: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    print("🚀 Starting Nutrifit Agent Service...")

    # Initialize MCP clients
    agent_manager.initialize_mcp_clients()

    # Initialize Redis (optional)
    redis_url = os.getenv("REDIS_URL")
    redis_password = os.getenv("REDIS_PASSWORD")
    enable_redis = os.getenv("ENABLE_REDIS_CACHE", "true").lower() == "true"

    if enable_redis and redis_url:
        try:
            global redis_client
            redis_client = redis.from_url(
                redis_url,
                password=redis_password if redis_password else None,
                decode_responses=True,
            )
            await redis_client.ping()
            print("✅ Redis connected")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            redis_client = None

    print("✅ Agent Service ready")

    yield  # Application runs

    # Shutdown
    print("🛑 Shutting down Agent Service...")

    # Cleanup MCP clients
    agent_manager.shutdown_mcp_clients()

    # Close Redis
    if redis_client:
        await redis_client.close()

    print("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Nutrifit Agent Service",
    description="AI-powered nutritional assistant with MCP tools",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Models
# ============================================


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str
    conversation_id: str
    tool_calls: list[str]
    agent_handoffs: list[str]  # List of agents involved (e.g., ["nutrizionista", "personal_trainer"])
    processing_time_ms: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str
    mcp_clients: Dict[str, str]
    redis: str
    agent_stats: Dict[str, Any]


# ============================================
# Endpoints
# ============================================


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring."""
    stats = agent_manager.get_stats()

    # Check Redis
    redis_status = "disconnected"
    if redis_client:
        try:
            await redis_client.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "error"

    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0",
        mcp_clients={
            "note": "MCP clients created per-user",
            "available": "user, meal, activity, profile",
        },
        redis=redis_status,
        agent_stats=stats,
    )


@app.post("/api/agent/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user),
) -> ChatResponse:
    """Non-streaming chat endpoint.

    Args:
        request: Chat request with message
        user: Authenticated user from JWT

    Returns:
        Agent response with tool calls
    """
    start_time = datetime.utcnow()

    user_id = user["user_id"]
    auth_token = user["token"]

    # Get swarm for user (router + nutrizionista + personal_trainer)
    swarm = await agent_manager.get_swarm_for_user(user_id, auth_token)

    # Run swarm
    try:
        result = swarm(request.message)

        # Extract response from swarm result
        # The final agent's message contains the response
        final_node = result.node_history[-1] if result.node_history else None
        response_text = ""
        
        if final_node and final_node.node_id in result.results:
            final_result = result.results[final_node.node_id]
            if hasattr(final_result, "result") and final_result.result:
                agent_result = final_result.result
                # Extract text from AgentResult message
                if hasattr(agent_result, "message") and agent_result.message:
                    content = agent_result.message.get("content", [])
                    if content and len(content) > 0:
                        response_text = content[0].get("text", "")
        
        # Fallback to accumulated results
        if not response_text and result.results:
            # Try to get text from any result
            for node_result in result.results.values():
                if hasattr(node_result, "result") and node_result.result:
                    agent_result = node_result.result
                    if hasattr(agent_result, "message") and agent_result.message:
                        content = agent_result.message.get("content", [])
                        if content and len(content) > 0:
                            response_text = content[0].get("text", "")
                            if response_text:
                                break
        
        # Extract tool calls and agent handoffs
        tool_calls = []
        agent_handoffs = []
        for node in result.node_history:
            agent_handoffs.append(node.node_id)
            if node.node_id in result.results:
                node_result = result.results[node.node_id]
                if hasattr(node_result, "result") and node_result.result:
                    agent_result = node_result.result
                    if hasattr(agent_result, "tool_calls") and agent_result.tool_calls:
                        tool_calls.extend([call["name"] for call in agent_result.tool_calls])
        
        conversation_id = getattr(result, "conversation_id", "default")

        # Cache conversation in Redis (optional)
        if redis_client:
            try:
                key = f"conversation:{user_id}:{conversation_id}"
                await redis_client.rpush(key, f"{request.message}|{response_text}")
                await redis_client.expire(key, 3600)  # 1 hour TTL
            except Exception as e:
                print(f"⚠️ Redis cache error: {e}")

        # Calculate processing time
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            tool_calls=tool_calls,
            agent_handoffs=agent_handoffs,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}") from e


@app.get("/api/agent/stream-sse")
async def stream_sse(
    message: str,
    user: Dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    """Server-Sent Events streaming endpoint.

    Args:
        message: User message (query param)
        user: Authenticated user from JWT

    Returns:
        SSE stream with agent responses
    """
    user_id = user["user_id"]
    auth_token = user["token"]

    # Get agent for user
    agent = await agent_manager.get_agent_for_user(user_id, auth_token)

    async def event_generator():
        """Generate SSE events."""
        try:
            # Stream agent response
            async for chunk in agent.stream(message):
                if hasattr(chunk, "content"):
                    yield f"data: {chunk.content}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.get("/api/agent/history")
async def get_history(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
) -> JSONResponse:
    """Get conversation history from Redis.

    Args:
        conversation_id: Conversation ID
        user: Authenticated user from JWT

    Returns:
        Conversation history as JSON
    """
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")

    user_id = user["user_id"]
    key = f"conversation:{user_id}:{conversation_id}"

    try:
        history = await redis_client.lrange(key, 0, -1)
        messages = []

        for entry in history:
            parts = entry.split("|", 1)
            if len(parts) == 2:
                messages.append({"user": parts[0], "assistant": parts[1]})

        return JSONResponse({"conversation_id": conversation_id, "messages": messages})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}") from e


@app.delete("/api/agent/session")
async def delete_session(user: Dict[str, Any] = Depends(get_current_user)) -> JSONResponse:
    """Delete user agent session (cleanup).

    Args:
        user: Authenticated user from JWT

    Returns:
        Success message
    """
    user_id = user["user_id"]
    agent_manager.remove_agent(user_id)

    return JSONResponse({"message": f"Session deleted for user {user_id}"})


# ============================================
# Run with uvicorn
# ============================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
    )
