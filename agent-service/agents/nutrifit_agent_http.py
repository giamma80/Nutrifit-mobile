"""Nutrifit Agent configuration with HTTP MCP integration.

This module implements the multi-agent Swarm architecture using HTTP transport
to communicate with FastMCP servers running as subprocesses.

Architecture:
    FastMCP Servers (HTTP subprocess) → HTTPToolAdapter → Strands Agent Tools
    
Risolve il problema del blocking STDIO handshake usando HTTP transport.
"""

import asyncio
import os
import logging
import subprocess
import time
from typing import Dict, Optional, List, Any
from pathlib import Path

import httpx
from strands import Agent
from strands.models.anthropic import AnthropicModel
from strands.multiagent import Swarm

from tools.http_tool_adapter import load_tools_from_url


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NutrifitAgentManager:
    """Manages Nutrifit multi-agent Swarm with HTTP MCP integration."""

    def __init__(self):
        """Initialize agent manager with HTTP MCP configuration."""
        self.swarms: Dict[str, Dict] = {}  # {user_id: {"swarm": Swarm, "created_at": timestamp}}
        self.mcp_processes: Dict[str, subprocess.Popen] = {}  # Subprocess HTTP servers
        self.mcp_server_pids: Dict[str, int] = {}  # Track PIDs for restart detection
        self.swarm_ttl = 3600  # TTL cache: 1 ora (swarm si ricarica dopo)
        
        # Environment configuration
        self.mcp_base_path = Path(os.getenv("MCP_BASE_PATH", "/app/MCP"))
        self.mcp_python_path = os.getenv("MCP_PYTHON_PATH", "/app/MCP/.venv/bin/python")
        self.graphql_endpoint = os.getenv("GRAPHQL_ENDPOINT", "http://nutrifit-backend:8080/graphql")
        
        # Anthropic Model configuration
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        model_id = os.getenv("STRANDS_MODEL", "claude-sonnet-4-20250514")
        
        self.anthropic_model = AnthropicModel(
            client_args={"api_key": anthropic_api_key},
            max_tokens=4096,
            model_id=model_id,
            params={"temperature": 0.7},
        )
        
        # MCP server configuration
        self.mcp_servers = {
            "user": {
                "path": self.mcp_base_path / "user-mcp" / "server_http.py",
                "url": "http://localhost:8004",
                "port": 8004,
            },
            "meal": {
                "path": self.mcp_base_path / "meal-mcp" / "server_http.py",
                "url": "http://localhost:8001",
                "port": 8001,
            },
            "activity": {
                "path": self.mcp_base_path / "activity-mcp" / "server_http.py",
                "url": "http://localhost:8002",
                "port": 8002,
            },
            "nutritional_profile": {
                "path": self.mcp_base_path / "nutritional-profile-mcp" / "server_http.py",
                "url": "http://localhost:8003",
                "port": 8003,
            },
        }
        
        # Verify MCP servers exist
        for name, config in self.mcp_servers.items():
            if not config["path"].exists():
                logger.warning(f"⚠️  MCP server not found: {name} at {config['path']}")
            else:
                logger.info(f"✅ MCP server found: {name} at {config['path']}")

    def start_mcp_servers(self) -> None:
        """Start HTTP MCP servers as background subprocesses.
        
        Called at app startup. Servers listen on localhost ports and stay alive
        for the entire application lifetime.
        """
        logger.info("🚀 Starting HTTP MCP servers...")
        
        for server_name, config in self.mcp_servers.items():
            server_path = config["path"]
            port = config["port"]
            
            if not server_path.exists():
                logger.error(f"❌ Cannot start {server_name}: file not found")
                continue
            
            try:
                logger.info(f"📝 Starting {server_name} on port {port}...")
                
                # Start subprocess
                process = subprocess.Popen(
                    [self.mcp_python_path, str(server_path)],
                    env={
                        **os.environ,
                        "GRAPHQL_ENDPOINT": self.graphql_endpoint,
                        "PORT": str(port),
                        "HOST": "127.0.0.1",
                    },
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                
                self.mcp_processes[server_name] = process
                self.mcp_server_pids[server_name] = process.pid
                logger.info(f"✅ {server_name} started (PID: {process.pid})")
            
            except Exception as e:
                logger.error(f"❌ Failed to start {server_name}: {e}")
        
        # Wait for servers to be ready
        logger.info("⏳ Waiting for servers to be ready...")
        time.sleep(2)  # Give servers time to start
        
        # Health check
        for server_name, config in self.mcp_servers.items():
            if server_name not in self.mcp_processes:
                continue
            
            try:
                response = httpx.get(f"{config['url']}/health", timeout=5.0)
                if response.status_code == 200:
                    logger.info(f"✅ {server_name} is healthy")
                else:
                    logger.warning(f"⚠️  {server_name} health check failed: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️  {server_name} health check failed: {e}")
        
        logger.info(f"✅ {len(self.mcp_processes)} MCP servers started")

    def stop_mcp_servers(self) -> None:
        """Stop all HTTP MCP servers and invalidate tool cache."""
        logger.info("🛑 Stopping HTTP MCP servers...")
        
        for server_name, process in self.mcp_processes.items():
            try:
                logger.info(f"⏳ Stopping {server_name} (PID: {process.pid})...")
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"✅ {server_name} stopped")
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️  Force killing {server_name}...")
                process.kill()
            except Exception as e:
                logger.warning(f"⚠️  Failed to stop {server_name}: {e}")
        
        self.mcp_processes.clear()
        self.mcp_server_pids.clear()
        
        # Invalidate all cached swarms (force tool reload on next use)
        logger.info("🔄 Invalidating all cached swarms...")
        self.swarms.clear()
        
        logger.info("✅ All MCP servers stopped and cache cleared")

    def _check_servers_alive(self) -> bool:
        """Check if MCP servers are still running with same PIDs.
        
        Returns:
            True if all servers alive, False if any restarted/died
        """
        for server_name, expected_pid in self.mcp_server_pids.items():
            process = self.mcp_processes.get(server_name)
            if not process:
                logger.warning(f"⚠️  {server_name} process not found")
                return False
            
            # Check if process still alive with same PID
            if process.poll() is not None:
                logger.warning(f"⚠️  {server_name} died (PID: {expected_pid})")
                return False
            
            if process.pid != expected_pid:
                logger.warning(f"⚠️  {server_name} PID changed ({expected_pid} → {process.pid})")
                return False
        
        return True

    async def _load_tools_from_server(self, server_name: str, auth_token: str) -> List:
        """Load tools from HTTP MCP server.
        
        Args:
            server_name: Name of server (meal, activity, nutritional_profile)
            auth_token: JWT token for authentication
            
        Returns:
            List of Tool objects
        """
        config = self.mcp_servers.get(server_name)
        if not config:
            logger.error(f"❌ Unknown server: {server_name}")
            return []
        
        url = config["url"]
        
        try:
            logger.info(f"📥 Loading tools from {server_name} ({url})...")
            tools = await load_tools_from_url(url, auth_token, timeout=30.0)
            logger.info(f"✅ Loaded {len(tools)} tools from {server_name}")
            return tools
        except Exception as e:
            logger.error(f"❌ Failed to load tools from {server_name}: {e}")
            return []

    def _create_router_agent(self, auth_token: str, user_tools: List, meal_tools: List, activity_tools: List, profile_tools: List) -> Agent:
        """Create router agent with limited tools for triage."""
        # Router needs only basic tools to understand user intent
        router_tools = []
        
        # User tools for authentication context
        router_tools.extend([t for t in user_tools if t.name in ["get_current_user"]])
        
        # Profile tools for understanding user context
        router_tools.extend([t for t in profile_tools if t.name in ["get_nutritional_profile"]])
        
        # Basic meal query tools
        router_tools.extend([t for t in meal_tools if t.name in ["get_daily_summary"]])
        
        # Basic activity query tools
        router_tools.extend([t for t in activity_tools if t.name in ["aggregate_activity_range"]])
        
        router = Agent(
            name="Router",
            instructions="""You are the routing agent for Nutrifit.
            
Your role:
1. Understand user intent from their message
2. Route to appropriate specialist:
   - Nutritionist: meal logging, food analysis, nutrition advice
   - Trainer: activity tracking, exercise, fitness goals
3. Use basic tools only to gather context for routing decisions
4. Delegate detailed work to specialists

Always be concise and route quickly.""",
            tools=router_tools,
            model=self.anthropic_model,
        )
        
        return router

    def _create_nutritionist_agent(self, auth_token: str, meal_tools: List, profile_tools: List) -> Agent:
        """Create nutritionist agent with meal and profile tools."""
        
        # Combine meal tools + profile tools
        nutritionist_tools = meal_tools + profile_tools
        
        nutritionist = Agent(
            name="Nutritionist",
            instructions="""You are an expert nutritionist for Nutrifit.

Your capabilities:
- Analyze meals from text, photos, or barcodes
- Track nutrition and provide advice
- Monitor daily/weekly nutrition progress
- Help users meet their nutritional goals

Always:
1. Be encouraging and supportive
2. Provide specific, actionable advice
3. Use tools to get accurate nutrition data
4. Respect user's dietary preferences and goals

Language: Communicate in Italian (user's preferred language).""",
            tools=nutritionist_tools,
            model=self.anthropic_model,
        )
        
        return nutritionist

    def _create_trainer_agent(self, auth_token: str, activity_tools: List, profile_tools: List) -> Agent:
        """Create trainer agent with activity and profile tools."""
        
        # Combine activity tools + profile tools
        trainer_tools = activity_tools + profile_tools
        
        trainer = Agent(
            name="Trainer",
            instructions="""You are an expert fitness trainer for Nutrifit.

Your capabilities:
- Track physical activity and exercise
- Monitor steps, calories burned, and workout progress
- Provide fitness advice and motivation
- Help users achieve their fitness goals

Always:
1. Be motivating and energetic
2. Provide specific, safe exercise recommendations
3. Use tools to track accurate activity data
4. Adapt advice to user's fitness level

Language: Communicate in Italian (user's preferred language).""",
            tools=trainer_tools,
            model=self.anthropic_model,
        )
        
        return trainer

    async def get_swarm_for_user(self, user_id: str, auth_token: str) -> Swarm:
        """Get or create Swarm for user with HTTP-loaded tools.
        
        Args:
            user_id: User ID
            auth_token: JWT token for tool authentication
            
        Returns:
            Swarm instance ready for conversation
        """
        # Check if MCP servers are still running (detect restarts)
        if not self._check_servers_alive():
            logger.warning("🔄 MCP servers changed, invalidating all swarms...")
            self.swarms.clear()
        
        # Check if user already has a swarm and if it's still valid (TTL)
        if user_id in self.swarms:
            swarm_data = self.swarms[user_id]
            created_at = swarm_data.get("created_at", 0)
            age = time.time() - created_at
            
            if age < self.swarm_ttl:
                logger.info(f"♻️  Reusing existing Swarm for user {user_id} (age: {int(age)}s)")
                return swarm_data["swarm"]
            else:
                logger.info(f"🔄 Swarm expired for user {user_id} (age: {int(age)}s), reloading tools...")
                del self.swarms[user_id]
        
        logger.info(f"🆕 Creating new Swarm for user {user_id}")
        
        # Load tools from HTTP servers
        user_tools = await self._load_tools_from_server("user", auth_token)
        meal_tools = await self._load_tools_from_server("meal", auth_token)
        activity_tools = await self._load_tools_from_server("activity", auth_token)
        profile_tools = await self._load_tools_from_server("nutritional_profile", auth_token)
        
        if not user_tools and not meal_tools and not activity_tools and not profile_tools:
            raise RuntimeError("❌ No tools loaded from any MCP server")
        
        logger.info(f"📊 Total tools: {len(user_tools)} user + {len(meal_tools)} meal + {len(activity_tools)} activity + {len(profile_tools)} profile")
        
        # Create agents
        nutritionist = self._create_nutritionist_agent(auth_token, meal_tools, profile_tools)
        trainer = self._create_trainer_agent(auth_token, activity_tools, profile_tools)
        router = self._create_router_agent(auth_token, user_tools, meal_tools, activity_tools, profile_tools)
        
        # Add handoff capabilities to router
        router.handoff_agents = [nutritionist, trainer]
        
        # Create Swarm
        swarm = Swarm(
            nodes=[router, nutritionist, trainer],
            entry_point=router,
            max_handoffs=20,
            max_iterations=20,
        )
        
        # Store swarm with timestamp
        self.swarms[user_id] = {
            "swarm": swarm,
            "created_at": time.time(),
        }
        
        logger.info(f"✅ Swarm created for user {user_id}")
        return swarm

    def cleanup_user_swarm(self, user_id: str) -> None:
        """Cleanup Swarm for user."""
        if user_id in self.swarms:
            logger.info(f"🗑️  Cleaning up Swarm for user {user_id}")
            del self.swarms[user_id]

    def serialize_swarm_state(self, user_id: str) -> Optional[dict]:
        """Serialize Swarm state for persistence."""
        if user_id not in self.swarms:
            return None
        
        swarm = self.swarms[user_id]["swarm"]
        try:
            return swarm.serialize_state()
        except Exception as e:
            logger.error(f"❌ Failed to serialize swarm state: {e}")
            return None

    def deserialize_swarm_state(self, user_id: str, state: dict) -> bool:
        """Restore Swarm state from persistence."""
        if user_id not in self.swarms:
            logger.warning(f"⚠️  Cannot restore state: no swarm for user {user_id}")
            return False
        
        swarm = self.swarms[user_id]["swarm"]
        try:
            swarm.deserialize_state(state)
            logger.info(f"✅ Restored swarm state for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to restore swarm state: {e}")
            return False


# Global singleton instance
agent_manager = NutrifitAgentManager()
