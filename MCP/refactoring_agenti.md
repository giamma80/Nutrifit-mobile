# Introduzione veloce — cosa va bene e cosa no

## Cosa va bene

Design funzionale degli MCP (FastMCP)
i tool sono ben definiti, pagine GraphQL coerenti e input modellati con Pydantic.
Uso di FastAPI per esporre l’agent service e Redis come storage opzionale: architettura classica e scalabile.
Implementazioni async (httpx, FastMCP async tools) in generale corrette.

## Problemi principali

1) Mismatch di pattern: stai ricostruendo meccanismi di discovery/lifecycle/IPC con HTTP quando Strands/MCP supportano nativamente lo STDIO. Questo ha portato a complessità non necessarie (PID tracking, TTL cache, health checks custom, ecc.).
2) Blocchi nell’event loop: chiamate sincrone potenzialmente bloccanti (es. swarm(...)) dentro handler async di FastAPI.
3) Adapter HTTP “anti-MCP”: l’HTTPToolAdapter è un REST bridge che duplica funzionalità che Strands si aspetta di usare tramite MCP nativo; contiene inoltre bug pratici (uso di asyncio.run() dentro loop, import mancanti, wrapper sincroni).
4) Lifecycle fragile / race conditions: initialize/shutdown dei client non awaitati o eseguiti in modo sincrono -> potenziali deadlock al boot / shutdown.
5) Auth per-user: il requisito per-user token è gestito meglio da STDIO (env del subprocess) — con HTTP serve comunque una soluzione per-user (server per-user o gateway) che annulla i benefici del riuso.
6) Incoerenze Redis / logging / error exposure: nomi chiave diversi, print/stack espliciti nelle risposte, ecc.

## Conclusione

per il nostro caso (agent container chiamato dalla webapp + bisogno di per-user token), STDIO è la scelta più coerente. Se però volete mantenere HTTP, va fatto come componente orchestrato esternamente (non spawnato e gestito manualmente dall’agent) e il codice deve essere semplificato.

# File per file — cosa correggere (con snippet)

1) app.py — problemi & patch

* Problemi principali *

* Chiamata sincrona al swarm in handler async (result = swarm(enriched_message)) → blocca event loop.
* lifespan: agent_manager.initialize_mcp_clients() e shutdown_mcp_clients() usati senza controllare se sono coroutine (potrebbero bloccare l’avvio / la chiusura).
* print(...) invece di logging.
* Incoerenza chiavi Redis (conv:{} vs conversation:{user}:{id}).
* Esposizione dettagli errore all’utente (str(e)).

Cambiamenti consigliati (snippet da applicare)

A) usare asyncio.to_thread + timeout quando chiami lo swarm:

```python

import asyncio
import logging

logger = logging.getLogger("nutrifit.agent")

SWARM_RUN_TIMEOUT = int(os.getenv("SWARM_RUN_TIMEOUT", "30"))

# dentro /api/agent/chat replace sync call con

try:
    # se swarm è sync -> to_thread
    result = await asyncio.wait_for(
        asyncio.to_thread(swarm, enriched_message),
        timeout=SWARM_RUN_TIMEOUT,
    )
except asyncio.TimeoutError:
    logger.warning("Swarm timeout")
    raise HTTPException(status_code=504, detail="Agent timeout")
except Exception:
    logger.exception("Swarm execution failed")
    raise HTTPException(status_code=500, detail="Agent internal error") 
```

B) rendere lifespan robusto (await o esecuzione in thread se sync):

```python
# dentro lifespan

if asyncio.iscoroutinefunction(agent_manager.initialize_mcp_clients):
    await agent_manager.initialize_mcp_clients()
else:
    await asyncio.to_thread(agent_manager.initialize_mcp_clients)

# e per shutdown

if asyncio.iscoroutinefunction(agent_manager.shutdown_mcp_clients):
    await agent_manager.shutdown_mcp_clients()
else:
    await asyncio.to_thread(agent_manager.shutdown_mcp_clients)
```

C) uniformare la key Redis e usare logging:

```python
def conv_key(user_id: str, conversation_id: str) -> str:
    return f"conversation:{user_id}:{conversation_id}"

# get_conversation_state -> richiede user_id e conversation_id

async def get_conversation_state(user_id: str, conversation_id: str):
    key = conv_key(user_id, conversation_id)
    
```

D) evitare di esporre dettagli d’errore:

```python
logger.exception("Agent error details")
raise HTTPException(status_code=500, detail="Agent internal error")
```

Perché: così eviti blocchi del worker uvicorn, migliori robustezza e logging.

2) http_tool_adapter.py

* Problemi principali *

* Tool non è importato / non si usa il decorator @tool di Strands.
* sync_wrapper usa asyncio.run() (scoppia se già esiste event loop).
* tool = Tool(...) non è garantito a livello di API Strands (in v1.18 si preferisce decorator).
* Nessun timeout per singola invocazione, nessun handling strutturato per error payload.
* L’adapter non è “MCP”: è un bridge REST, che rompe l’introspezione e la compatibilità.

Patch consigliate — versione compatibile e sicura

1. Rimuovere sync_wrapper e non usare asyncio.run().
2. Creare i tool usando @tool_decorator dinamicamente.
3. Aggiungere timeout per invocazione e migliorare error handling.
Snippet sostitutivo per load_tools (essenziale):

```python
from strands import tool as tool_decorator
from typing import Callable

# inside class HTTPToolAdapter

def _make_tool_callable(self, tool_name: str, timeout_per_call: float = 10.0) -> Callable:
    async def tool_function(**kwargs):
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.base_url}/tools/{tool_name}",
                    json={"arguments": kwargs},
                    timeout=timeout_per_call
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("error"):
                    raise Exception(payload["error"])
                return payload.get("result")
            except httpx.HTTPError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise

    return tool_function

async def load_tools(self):
    specs = await self.list_tools()
    tools = []
    for spec in specs:
        name = spec["name"]
        fn = self._make_tool_callable(name)
        # create decorated tool for strands
        @tool_decorator(name=name, description=spec.get("description", ""))
        async def dyn_tool(**kwargs):
            return await fn(**kwargs)

        tools.append(dyn_tool)
    return tools
```

Nota: mantenere l’adapter solo se hai MCP HTTP remoti e non puoi usare STDIO. Altrimenti deprecate.

3) /mnt/data/nutrifit_agent_http.py (il modulo HTTP manager)

* Problemi principali *

* Gestione manuale di subprocess HTTP (PID tracking, spawn/kill) → troppa complessità.
* Cache TTL e reload difficile da invalidare.
* Health probes/port conflicts.
Opzioni
A1 (consigliata): eliminare l’approccio spawn-internamente e spostare il lifecycle HTTP all’orchestrator (docker-compose / k8s). L’agent semplicemente probe /health e load_tools_from_url.
A2 (se insistete su spawn): semplificare: non mantenere 4 server in memoria, usare una sola factory parametrizzata, do not PID track (o farlo con libreria di process manager testata).
Patch suggerita (semplificazione probe + load once)

```python
async def ensure_server_ready(url, timeout=30):
    import httpx, time
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{url}/health", timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            await asyncio.sleep(0.5)
    return False

# when starting, call

if not await ensure_server_ready(url):
    raise RuntimeError("MCP HTTP server not ready")

tools = await load_tools_from_url(url, auth_token)
if not tools:
    raise RuntimeError("No tools loaded")

```

Se rimanete su HTTP: spostate PID/lifecycle in orchestration e rendete agent stateless rispetto al processo.

4) /mnt/data/nutrifit_agent_mcp.py (STDIO manager)

* Problemi principali *

* Ottimo pattern per per-user token. Ma attenzione a buffering/handshake STDIO (cause comuni di blocco).
* Potrebbe non usare -u / PYTHONUNBUFFERED quando avvia Python subprocess.
* initialize_mcp_clients() / shutdown_mcp_clients() devono essere coroutine o eseguite in background senza bloccare FastAPI.

Patch concrete
A) assicurarsi che la creazione di StdioServerParameters usi Python non bufferato:

```python
from mcp.transport.stdio import StdioServerParameters

server_params = StdioServerParameters(
    command="/usr/bin/python3",
    args=["-u", str(server_script_path)],
    env={
        "GRAPHQL_ENDPOINT": self.graphql_endpoint,
        "AUTH0_TOKEN": auth_token,
        "PYTHONUNBUFFERED": "1",
    }
)
```

B) rendere initialize/shutdown compatibili con lifespan:

in agent_manager

```python
async def initialize_mcp_clients(self):
    # if starts are blocking, use asyncio.to_thread
    await asyncio.to_thread(self._sync_initialize)

async def shutdown_mcp_clients(self):
    await asyncio.to_thread(self._sync_shutdown)
```

C) assicurare per-user isolation: get_swarm_for_user(user_id, auth_token) deve creare/return swarm unico per user (non singleton globale) e proteggere accessi concorrenti con asyncio.Lock().

5) pyproject.toml

* Problemi / raccomandazioni *

- Assicurati che le versioni di strands e mcp siano compatibili: specifica strands-agents==1.18.0 o >=1.18.0,<1.19.
* Aggiungi fastmcp, httpx, redis espliciti.
* Blocca httpx a una release stabile (es. 0.24.*), evita wildcard troppo ampie.

Esempio snippet:
'''toml
[tool.poetry.dependencies]
python = "^3.11"
strands-agents = "==1.18.0"
mcp = ">=1.1.2,<1.2"
fastmcp = ">=0.3.0"
httpx = ">=0.24.0,<0.25"
redis = ">=5.0.0"
fastapi = "^0.95.0"
uvicorn = "^0.22.0"
'''

Perché: evitare incompatibilità runtime con API cambiate.

6) MCP server (FastMCP) — osservazioni e piccoli fiix

1. Timeout singola richiesta: DEFAULT_TIMEOUT è ok, ma nelle chiamate httpx riusa lo stesso client (fai async with httpx.AsyncClient(...) as client) — OK. Consiglio di passare response.raise_for_status() e poi result = response.json() come fai, ma aggiungi try/except con logging dettagliato per errori GraphQL.
2. Controllo if "errors" in result: corretto. Aggiungi logging con logger.exception(...) per errori GraphQL e includi query hash per debug.
3. mcp.run(): ok. Assicurati che il server MCP sia avviato con PYTHONUNBUFFERED=1 se lo spawnate come subprocess STDIO.
Esempio miglioramento graphql_query con logging:

```python
import logging
logger = logging.getLogger("nutrifit.mcp")

async def graphql_query(query: str, variables: Optional[dict] = None) -> dict:
    ...
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        try:
            response = await client.post(GRAPHQL_ENDPOINT, json=payload)
            response.raise_for_status()
            result = response.json()
            if "errors" in result:
                logger.error("GraphQL errors: %s -- query: %s", result["errors"], query[:200])
                raise Exception(...)
            return result["data"]
        except httpx.HTTPError:
            logger.exception("HTTP error calling GraphQL")
            raise
```

4. Entrypoint: quando spawnato come STDIO subprocess assicurati di invocare python -u server_mcp.py o impostare PYTHONUNBUFFERED=1 nell'env.

# PRIORITà OPERATIVA

1. Bloccare il bug più pericoloso: sostituire result = swarm(...) in app.py con await asyncio.to_thread(... ) + timeout (vedi snippet). (Alta priorità)
2. Aggiungere -u / PYTHONUNBUFFERED=1 per tutti i subprocess STDIO nel manager (nutrifit_agent_mcp.py). (Alta)
3. Rimuovere asyncio.run() dal HTTPToolAdapter e creare tool con @tool_decorator dinamico oppure deprecare l’adapter e usare STDIO. (Alta)
4. Uniformare keys Redis e cambiare print in logging. (Media)
5. Aggiornare pyproject.toml per version pin di strands-agents e mcp. (Media)
6. Decidere: STDIO (recommended) o HTTP orchestrated; se HTTP allora spostate spawn/lifecycle fuori dall’agent e semplificate il manager. (Arch decision, alta impatto)
7. Aggiungere test end-to-end: fake MCP (minimal tool) + agent + app + concurrent calls. (Media)
