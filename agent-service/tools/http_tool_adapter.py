"""
HTTP Tool Adapter for MCP Servers

Carica tools da server MCP HTTP e crea funzioni Python decorate con @tool per Strands Agent.
Risolve il problema del blocking STDIO handshake usando HTTP transport.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable

import httpx
from strands import tool as tool_decorator


logger = logging.getLogger(__name__)


class HTTPToolAdapter:
    """
    Adapter per caricare tools da MCP server HTTP.
    
    Pattern:
    1. Chiama GET /tools per ottenere lista tools
    2. Per ogni tool, crea un Tool object con funzione che chiama POST /tools/{name}
    3. Ritorna lista di Tool objects per Strands Agent
    """
    
    def __init__(
        self,
        base_url: str,
        auth_token: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Inizializza adapter.
        
        Args:
            base_url: URL base del server MCP (es: "http://localhost:8001")
            auth_token: Token di autenticazione da passare al server
            timeout: Timeout per richieste HTTP (secondi)
            max_retries: Numero massimo di tentativi in caso di fallimento
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries
        
        # HTTP client configurato con retry
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    
    async def close(self):
        """Chiude il client HTTP."""
        await self.client.aclose()
    
    async def health_check(self) -> bool:
        """
        Verifica che il server MCP sia raggiungibile.
        
        Returns:
            True se server risponde, False altrimenti
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed for {self.base_url}: {e}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Ottiene lista dei tools disponibili dal server.
        
        Returns:
            Lista di dict con name, description, parameters per ogni tool
        
        Raises:
            httpx.HTTPError: Se richiesta fallisce
        """
        response = await self.client.get(f"{self.base_url}/tools")
        response.raise_for_status()
        return response.json()
    
    def _create_tool_function(self, tool_name: str):
        """
        Crea funzione che chiama il tool via HTTP.
        
        Args:
            tool_name: Nome del tool sul server MCP
        
        Returns:
            Funzione async che accetta **kwargs e chiama il tool
        """
        async def tool_function(**kwargs) -> Any:
            """Esegue tool via HTTP POST."""
            for attempt in range(self.max_retries):
                try:
                    response = await self.client.post(
                        f"{self.base_url}/tools/{tool_name}",
                        json={"arguments": kwargs},
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    # Check for errors in response
                    if result.get("error"):
                        raise Exception(f"Tool error: {result['error']}")
                    
                    return result.get("result")
                
                except httpx.HTTPError as e:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Tool {tool_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                        await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Tool {tool_name} failed after {self.max_retries} attempts: {e}")
                        raise
        
        return tool_function
    
    async def load_tools(self) -> List[Tool]:
        """
        Carica tutti i tools dal server MCP e crea Tool objects.
        
        Returns:
            Lista di Tool objects pronti per Strands Agent
        
        Raises:
            httpx.HTTPError: Se comunicazione con server fallisce
        """
        # Get tools metadata
        tools_specs = await self.list_tools()
        
        logger.info(f"Loading {len(tools_specs)} tools from {self.base_url}")
        
        # Create Tool objects
        tools = []
        for spec in tools_specs:
            tool_name = spec["name"]
            
            # Create callable function
            tool_function = self._create_tool_function(tool_name)
            
            # Wrap in sync function for Strands (se necessario)
            def sync_wrapper(**kwargs):
                return asyncio.run(tool_function(**kwargs))
            
            # Create Tool object
            tool = Tool(
                name=tool_name,
                description=spec["description"],
                function=tool_function,  # Strands supporta async
                parameters=spec.get("parameters", {}),
            )
            
            tools.append(tool)
            logger.debug(f"✅ Loaded tool: {tool_name}")
        
        logger.info(f"✅ Successfully loaded {len(tools)} tools from {self.base_url}")
        return tools


async def load_tools_from_url(
    url: str,
    auth_token: str,
    timeout: float = 30.0,
) -> List[Tool]:
    """
    Helper function per caricare tools da URL in modo semplice.
    
    Args:
        url: URL base del server MCP
        auth_token: Token di autenticazione
        timeout: Timeout richieste HTTP
    
    Returns:
        Lista di Tool objects
    
    Example:
        tools = await load_tools_from_url(
            "http://localhost:8001",
            auth_token="eyJhbG...",
        )
        agent = Agent(name="Nutritionist", tools=tools)
    """
    adapter = HTTPToolAdapter(url, auth_token, timeout)
    
    try:
        # Health check
        if not await adapter.health_check():
            logger.warning(f"Health check failed for {url}, attempting to load anyway...")
        
        # Load tools
        tools = await adapter.load_tools()
        
        return tools
    
    finally:
        await adapter.close()
