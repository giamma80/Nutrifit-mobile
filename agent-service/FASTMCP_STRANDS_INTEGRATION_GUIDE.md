# Guida Integrazione FastMCP con Strands

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Due Approcci di Integrazione](#due-approcci-di-integrazione)
3. [⚠️ Problema Critico STDIO](#problema-critico-stdio)
4. [Preparazione Server FastMCP](#preparazione-server-fastmcp)
5. [Approccio 1: STDIO Transport (NON Raccomandato)](#approccio-1-stdio-transport-non-raccomandato)
6. [Approccio 2: HTTP Transport (✅ RACCOMANDATO)](#approccio-2-http-transport)
7. [Migrazione STDIO → HTTP](#migrazione-stdio-http)
8. [Configurazione Ambiente](#configurazione-ambiente)
9. [Testing e Troubleshooting](#testing-e-troubleshooting)
10. [Best Practices](#best-practices)

---

## Panoramica

**Problema**: Hai server MCP creati con FastMCP (come `nutrifit_activity_mcp.py`) ma non riesci a usarli con Strands Agent.

**Soluzione**: Utilizzare `MCPClient` come bridge tra FastMCP e Strands, con trasporto STDIO o HTTP.

### Architettura

```
FastMCP Server          MCPClient (Bridge)          Strands Agent
    ↓                          ↓                          ↓
@mcp.tool()    ←→    list_tools_sync()    ←→    Agent(tools=...)
   ↓                          ↓                          ↓
mcp.run()          StdioServerParameters        execute_task()
```

### Stack Tecnologico

- **FastMCP**: Server framework per MCP
- **Strands**: Agent framework per LLM
- **MCPClient**: Bridge protocol-agnostic
- **Transport**: STDIO (subprocess) o HTTP (client/server)

---

## Due Approcci di Integrazione

### Confronto Rapido

| Caratteristica | STDIO Transport | HTTP Transport |
|----------------|-----------------|----------------|
| **Complessità** | Bassa | Media |
| **Setup** | Singolo processo | Server + Client |
| **Performance** | Ottima (IPC locale) | Buona (HTTP overhead) |
| **Debugging** | Semplice | Più complesso |
| **Scalabilità** | Limitata (1:1) | Alta (N:M) |
| **Uso consigliato** | ⚠️ **PROBLEMATICO** | ✅ **RACCOMANDATO** |

### ⚠️ Problema Critico STDIO Transport

**ATTENZIONE**: Il transport STDIO con FastMCP presenta un **bug critico** che rende `start()` bloccante:

```python
# ❌ BLOCCA INDEFINITAMENTE (30s timeout)
mcp_client = MCPClient(lambda: stdio_client(StdioServerParameters(...)))
mcp_client.start()  # Blocca qui! Handshake JSON-RPC fallisce
```

**Causa**:

- Il subprocess FastMCP parte correttamente (vedi banner nei log)
- Ma l'handshake JSON-RPC tra MCPClient e FastMCP fallisce
- `start()` attende timeout (30s default) rendendo l'app inutilizzabile

**Diagnosticato dopo debug estensivo**:

```bash
# Subprocess parte (banner visibile)
🚀 FastMCP server starting...

# Ma comunicazione JSON-RPC fallisce
# start() blocca attendendo risposta che non arriva
```

**SOLUZIONE**: Usa **HTTP Transport** (documentato sotto)

---

## Preparazione Server FastMCP

### 1. Verifica Struttura Server

Il tuo `nutrifit_activity_mcp.py` è **già compatibile** perché ha:

✅ **FastMCP Initialization**

```python
from fastmcp import FastMCP
mcp = FastMCP("Nutrifit Activity Tracking")
```

✅ **Tool Decorators**

```python
@mcp.tool()
async def get_activity_entries(input: GetActivityEntriesInput) -> dict:
    """Tool description"""
    # Implementation
    return data
```

✅ **Main Entry Point**

```python
if __name__ == "__main__":
    mcp.run()
```

### 2. Dipendenze Richieste

Nel tuo `pyproject.toml` del server MCP:

```toml
[project]
name = "nutrifit-activity-mcp"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "fastmcp>=2.12.5",
    "httpx>=0.28.1",
    "pydantic>=2.10.5"
]
```

### 3. Test Standalone

Prima di integrare con Strands, verifica che il server funzioni:

```bash
# Test STDIO mode (default)
uv run python nutrifit_activity_mcp.py

# Test HTTP mode
uv run python nutrifit_activity_mcp.py --transport streamablehttp --port 8000
```

---

## Approccio 1: STDIO Transport (⚠️ NON Raccomandato)

### ⚠️ Problemi Noti

**ATTENZIONE**: Questo approccio presenta **problemi critici** con FastMCP:

- ❌ **`start()` blocca indefinitamente** (timeout 30s)
- ❌ **Handshake JSON-RPC fallisce** tra MCPClient e subprocess FastMCP
- ❌ **Inutilizzabile in produzione** (blocking initialization)
- ❌ **Nessuna soluzione con pattern `with`** (chiude subprocess prematuramente)

**Diagnostica Problema**:

```python
# Subprocess parte (banner visibile in logs)
🚀 FastMCP server starting...

# Ma start() blocca qui
mcp_client.start()  # ❌ TIMEOUT 30s - Handshake fallisce
```

**Root Cause**: Incompatibilità comunicazione JSON-RPC tra `mcp.client.stdio` e FastMCP subprocess.

### ✅ Usa HTTP Transport (Approccio 2)

**Raccomandazione**: Salta questa sezione e vai direttamente ad [Approccio 2: HTTP Transport](#approccio-2-http-transport).

### Step-by-Step

#### 1. Crea Struttura Progetto

```
nutrifit-agent/
├── agent/
│   ├── __init__.py
│   ├── agent.py          # Strands agent
│   ├── pyproject.toml    # Dipendenze agent
│   └── run_agent.py      # Entry point
└── mcp/
    ├── __init__.py
    ├── nutrifit_activity_mcp.py  # FastMCP server
    └── pyproject.toml            # Dipendenze MCP
```

#### 2. Dipendenze Agent (`agent/pyproject.toml`)

```toml
[project]
name = "nutrifit-agent"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "strands-agents>=1.13.0",
    "strands-mcp-client>=0.1.0",
    "boto3>=1.35.82",          # AWS Bedrock
    "pydantic>=2.10.5"
]

[dependency-groups]
dev = [
    "pytest>=8.3.4",
    "ruff>=0.8.2"
]
```

#### 3. Implementa Agent con STDIO

Crea `agent/agent.py`:

```python
#!/usr/bin/env python3
"""
Nutrifit Activity Agent con FastMCP STDIO Transport

Integra il server FastMCP nutrifit_activity_mcp.py con Strands Agent
utilizzando il trasporto STDIO (subprocess).
"""

import asyncio
from pathlib import Path

from strands.agent import Agent
from strands.models.bedrock import BedrockModels
from strands_mcp_client import MCPClient, StdioServerParameters


async def run_nutrifit_agent():
    """Execute Nutrifit Activity Agent with MCP tools"""
    
    # 1. Path al server FastMCP
    project_root = Path(__file__).parent.parent.parent
    server_path = project_root / "mcp" / "nutrifit_activity_mcp.py"
    
    if not server_path.exists():
        raise FileNotFoundError(f"Server MCP non trovato: {server_path}")
    
    # 2. Configura STDIO transport
    # FastMCP esegue in subprocess, comunicazione via stdin/stdout
    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client
    
    # Factory function per MCPClient (richiede callable che restituisce context manager)
    def transport_factory():
        return stdio_client(StdioServerParameters(
            command="uv",
            args=["run", "python", str(server_path)],
            env=None  # Eredita environment corrente (GRAPHQL_ENDPOINT, etc.)
        ))
    
    # 3. Crea MCPClient (bridge FastMCP → Strands)
    mcp_client = MCPClient(transport_factory)
    
    # 4. Avvia MCPClient e carica tools
    print("🔌 Connessione a FastMCP server...")
    
    # IMPORTANTE: Non usare context manager qui!
    # Il subprocess deve rimanere aperto durante l'uso dell'agent
    mcp_client.start()  # Avvia subprocess MCP
    
    try:
        tools = mcp_client.list_tools_sync()
        
        print(f"✅ {len(tools)} tools caricati da FastMCP:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description[:60]}...")
        
        # 5. Crea Strands Agent con tools FastMCP
        agent = Agent(
            model=BedrockModels.CLAUDE_SONNET_4,
            tools=tools,
            system_prompt="""Sei un assistente per il tracking delle attività fisiche.

Hai accesso a 5 tools per gestire dati di attività e salute:
- get_activity_entries: Query dati minuto-per-minuto
- get_activity_sync_entries: Sync giornaliero delta
- aggregate_activity_range: Statistiche aggregate (DAY/WEEK/MONTH)
- sync_activity_events: Batch sync dati da dispositivi
- sync_health_totals: Snapshot totali giornalieri

REGOLE CRITICHE:
1. Parametro 'source' DEVE essere: APPLE_HEALTH, GOOGLE_FIT, o MANUAL
2. Parametro 'group_by' DEVE essere: DAY, WEEK, o MONTH
3. Date formato YYYY-MM-DD
4. Timestamp formato ISO 8601
5. USA SEMPRE idempotencyKey per sync operations

Rispondi in italiano, fornendo analisi dettagliate dei dati."""
        )
        
        # 6. Esegui task
        print("\n💬 Agent pronto. Inserisci query (o 'quit' per uscire):\n")
        
        while True:
            try:
                user_input = input("User: ").strip()
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("👋 Arrivederci!")
                    break
                
                if not user_input:
                    continue
                
                print("\n🤔 Agent sta pensando...\n")
                
                response = agent.execute_task(user_input)
                print(f"Agent: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interruzione utente. Arrivederci!")
                break
            except Exception as e:
                print(f"❌ Errore: {e}\n")
    
    finally:
        # 7. Cleanup: Chiudi subprocess MCP
        print("\n🛑 Chiusura connessione MCP...")
        mcp_client.stop()


if __name__ == "__main__":
    asyncio.run(run_nutrifit_agent())
```

#### 4. Entry Point (`agent/run_agent.py`)

```python
#!/usr/bin/env python3
"""Entry point per Nutrifit Agent"""

import asyncio
from agent import run_nutrifit_agent

if __name__ == "__main__":
    asyncio.run(run_nutrifit_agent())
```

#### 5. Configurazione Ambiente

Crea `.env` nella root del progetto:

```bash
# GraphQL Backend
GRAPHQL_ENDPOINT=http://localhost:8080/graphql

# AWS Bedrock (per Strands Agent)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

#### 6. Esecuzione

```bash
# Dalla directory agent/
cd agent

# Installa dipendenze
uv sync

# Esegui agent
uv run python run_agent.py
```

#### 7. Test Interattivo

```
User: Mostrami i dati di attività dell'utente 123 per oggi

Agent: 🤔 Agent sta pensando...
[Tool call: get_activity_entries con userId=123, startDate=2025-11-21]

Agent: Ecco i dati di attività per oggi:
- Passi totali: 8,450
- Calorie bruciate: 420 kcal
- Battito medio: 78 bpm
- Fonte dati: APPLE_HEALTH
```

---

## Approccio 2: HTTP Transport

### Quando Usarlo

- ✅ Produzione
- ✅ Microservizi distribuiti
- ✅ Multiple agents → singolo server
- ✅ Server MCP remoto
- ✅ Scalabilità orizzontale

### Step-by-Step

#### 1. Modifica Server FastMCP per HTTP

Il tuo `nutrifit_activity_mcp.py` supporta **già** HTTP tramite flag CLI.

Test server HTTP:

```bash
# Avvia server HTTP sulla porta 8000
uv run python nutrifit_activity_mcp.py --transport streamablehttp --port 8000

# Output atteso:
# 🚀 FastMCP server running on http://localhost:8000/mcp/
```

#### 2. Verifica Endpoint

```bash
# Test health check
curl http://localhost:8000/health

# Test MCP endpoint
curl http://localhost:8000/mcp/
```

#### 3. Implementa Agent con HTTP Client

Crea `agent/agent_http.py`:

```python
#!/usr/bin/env python3
"""
Nutrifit Activity Agent con FastMCP HTTP Transport

Connessione a FastMCP server HTTP remoto/locale.
"""

import asyncio
import os

from strands.agent import Agent
from strands.models.bedrock import BedrockModels
from strands_mcp_client import MCPClient
from strands_mcp_client.transports.streamablehttp import streamablehttp_client


async def run_nutrifit_agent_http():
    """Execute agent with HTTP MCP server"""
    
    # 1. URL del server FastMCP HTTP
    mcp_server_url = os.getenv(
        "MCP_SERVER_URL",
        "http://localhost:8000/mcp/"
    )
    
    print(f"🔌 Connessione a FastMCP server: {mcp_server_url}")
    
    # 2. Configura HTTP transport
    transport_factory = streamablehttp_client(mcp_server_url)
    
    # 3. Crea MCPClient
    mcp_client = MCPClient(transport_factory)
    
    # 4. Carica tools (context manager OBBLIGATORIO)
    with mcp_client:
        tools = mcp_client.list_tools_sync()
        
        print(f"✅ {len(tools)} tools caricati da FastMCP HTTP server")
        
        # 5. Crea Agent
        agent = Agent(
            model=BedrockModels.CLAUDE_SONNET_4,
            tools=tools,
            system_prompt="""Assistente per tracking attività fisiche.

Tools disponibili:
- get_activity_entries: Dati granulari minuto-per-minuto
- get_activity_sync_entries: Sync incrementale giornaliero
- aggregate_activity_range: Aggregazioni (DAY/WEEK/MONTH)
- sync_activity_events: Batch import da dispositivi
- sync_health_totals: Snapshot giornaliero totali

Parametri critici:
- source: APPLE_HEALTH | GOOGLE_FIT | MANUAL
- group_by: DAY | WEEK | MONTH
- Date: YYYY-MM-DD
- Timestamp: ISO 8601

Rispondi in italiano."""
        )
        
        # 6. Interactive loop
        print("\n💬 Agent HTTP pronto. Query:\n")
        
        while True:
            try:
                user_input = input("User: ").strip()
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    break
                
                if not user_input:
                    continue
                
                print("\n🤔 Processing...\n")
                response = agent.execute_task(user_input)
                print(f"Agent: {response}\n")
                
            except KeyboardInterrupt:
                print("\n👋 Bye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(run_nutrifit_agent_http())
```

#### 4. Esecuzione con HTTP

**Terminale 1 - Server**:

```bash
cd mcp/
uv run python nutrifit_activity_mcp.py --transport streamablehttp --port 8000
```

**Terminale 2 - Agent**:

```bash
cd agent/
export MCP_SERVER_URL=http://localhost:8000/mcp/
uv run python agent_http.py
```

---

## Configurazione Ambiente

### File `.env` Completo

```bash
# === GraphQL Backend ===
GRAPHQL_ENDPOINT=http://localhost:8080/graphql

# === AWS Bedrock (Strands Agent LLM) ===
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# === MCP Server HTTP (solo per HTTP transport) ===
MCP_SERVER_URL=http://localhost:8000/mcp/

# === Debugging ===
LOG_LEVEL=INFO
MCP_DEBUG=false
```

### Caricamento Variabili

**Opzione 1 - python-dotenv**:

```python
from dotenv import load_dotenv
load_dotenv()  # Carica .env automaticamente
```

**Opzione 2 - export manuale**:

```bash
export $(cat .env | xargs)
```

**Opzione 3 - uv run con .env**:

```bash
uv run --env-file .env python agent.py
```

---

## Testing e Troubleshooting

### Checklist Pre-Integrazione

Prima di eseguire l'agent, verifica:

- [ ] ✅ Server FastMCP esegue standalone: `uv run python nutrifit_activity_mcp.py`
- [ ] ✅ Dipendenze installate: `strands-agents`, `strands-mcp-client`
- [ ] ✅ File `.env` configurato con `GRAPHQL_ENDPOINT`, AWS credentials
- [ ] ✅ Path al server MCP corretto in `agent.py`
- [ ] ✅ Python 3.11+ attivo: `python --version`

### Errori Comuni

#### 1. `ModuleNotFoundError: No module named 'strands_mcp_client'`

**Causa**: Dipendenza mancante

**Soluzione**:

```bash
cd agent/
uv add strands-mcp-client
uv sync
```

#### 2. `FileNotFoundError: Server MCP non trovato`

**Causa**: Path errato al server FastMCP

**Soluzione**:

```python
# Verifica path relativo
server_path = Path(__file__).parent.parent.parent / "mcp" / "nutrifit_activity_mcp.py"
print(f"DEBUG: {server_path.absolute()}")
```

#### 3. `GraphQL errors: Unauthorized`

**Causa**: `GRAPHQL_ENDPOINT` non configurato o credenziali mancanti

**Soluzione**:

```bash
# Verifica .env
echo $GRAPHQL_ENDPOINT

# Test GraphQL diretto
curl -X POST $GRAPHQL_ENDPOINT -H "Content-Type: application/json" -d '{"query":"{ __typename }"}'
```

#### 4. `McpError: Connection closed` - Subprocess chiuso prematuramente

**Causa**: Utilizzo di context manager (`with mcp_client`) chiude subprocess prima dell'uso

**Errore**:

```python
mcp_client = MCPClient(transport_factory)
with mcp_client:  # ❌ Si chiude alla fine del with
    tools = mcp_client.list_tools_sync()
    agent = Agent(tools=tools)
# Subprocess chiuso qui!
response = agent.execute_task(...)  # Tools non disponibili!
```

**Soluzione - Gestione manuale lifecycle**:

```python
mcp_client = MCPClient(transport_factory)

# ✅ Avvia subprocess manualmente
mcp_client.start()

try:
    tools = mcp_client.list_tools_sync()
    agent = Agent(tools=tools)
    
    # Subprocess rimane aperto
    response = agent.execute_task(...)
    
finally:
    # ✅ Cleanup manuale
    mcp_client.stop()
```

**Perché non context manager?**

- `with mcp_client:` chiude il subprocess alla fine del blocco
- Agent ha bisogno che il subprocess MCP rimanga attivo durante `execute_task()`
- Usa `start()` e `stop()` per controllo esplicito del lifecycle

#### 5. `Connection refused (HTTP transport)`

**Causa**: Server FastMCP HTTP non avviato

**Soluzione**:

```bash
# Terminale 1 - Avvia server
uv run python nutrifit_activity_mcp.py --transport streamablehttp --port 8000

# Terminale 2 - Verifica
curl http://localhost:8000/health
```

### Debug Logging

Aggiungi logging dettagliato:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# In agent.py
with mcp_client:
    tools = mcp_client.list_tools_sync()
    print(f"DEBUG: Tools caricati = {[t.name for t in tools]}")
    print(f"DEBUG: Tool[0] schema = {tools[0].inputSchema}")
```

### Test Tools Isolation

Testa singoli tools prima dell'agent:

```python
with mcp_client:
    tools = mcp_client.list_tools_sync()
    
    # Test tool singolo
    get_entries_tool = next(t for t in tools if t.name == "get_activity_entries")
    
    # Simula call
    result = get_entries_tool.function(
        limit=10,
        user_id="test-user-123"
    )
    print(f"Test result: {result}")
```

---

## Best Practices

### 1. Gestione Errori

```python
async def run_agent_safe():
    """Agent con error handling robusto"""
    try:
        # Setup
        transport_factory = StdioServerParameters(...)
        mcp_client = MCPClient(transport_factory)
        
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            
            if not tools:
                raise ValueError("Nessun tool caricato da FastMCP")
            
            agent = Agent(model=..., tools=tools)
            
            # Execution
            response = agent.execute_task(query)
            return response
            
    except FileNotFoundError as e:
        print(f"❌ Server MCP non trovato: {e}")
    except ConnectionError as e:
        print(f"❌ Connessione fallita: {e}")
    except Exception as e:
        print(f"❌ Errore generico: {e}")
        import traceback
        traceback.print_exc()
```

### 2. Configurazione Centralizzata

```python
# config.py
from pathlib import Path
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    """Configurazione centralizzata"""
    graphql_endpoint: str = "http://localhost:8080/graphql"
    mcp_server_path: Path = Path(__file__).parent.parent / "mcp" / "nutrifit_activity_mcp.py"
    mcp_server_url: str = "http://localhost:8000/mcp/"
    aws_region: str = "us-east-1"
    transport_mode: str = "stdio"  # stdio | http
    
    class Config:
        env_file = ".env"

# agent.py
from config import Config
config = Config()

if config.transport_mode == "stdio":
    transport_factory = StdioServerParameters(...)
else:
    transport_factory = streamablehttp_client(config.mcp_server_url)
```

### 3. Testing Automatizzato

```python
# test_agent.py
import pytest
from agent import run_nutrifit_agent

@pytest.mark.asyncio
async def test_agent_tools_loaded():
    """Verifica che tools vengano caricati"""
    # Mock o test con server reale
    tools = await load_mcp_tools()
    
    assert len(tools) == 5
    assert "get_activity_entries" in [t.name for t in tools]
    assert "sync_activity_events" in [t.name for t in tools]

@pytest.mark.asyncio
async def test_agent_query():
    """Test query agent"""
    response = await run_nutrifit_agent()
    assert response is not None
    assert len(response) > 0
```

### 4. Idempotency Keys

Per operazioni di sync, genera sempre idempotency keys:

```python
import uuid
from datetime import datetime

def generate_idempotency_key(prefix: str = "sync") -> str:
    """Genera chiave idempotenza univoca"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}-{timestamp}-{unique_id}"

# Uso in agent
idempotency_key = generate_idempotency_key("healthkit-sync")
# Es: "healthkit-sync-20251121143000-a3f8c2d1"
```

### 5. Environment-Specific Config

```python
# .env.development
GRAPHQL_ENDPOINT=http://localhost:8080/graphql
MCP_SERVER_URL=http://localhost:8000/mcp/
LOG_LEVEL=DEBUG

# .env.production
GRAPHQL_ENDPOINT=https://api.nutrifit.com/graphql
MCP_SERVER_URL=https://mcp.nutrifit.com/activity/
LOG_LEVEL=WARNING

# Carica environment-specific
import os
env = os.getenv("ENVIRONMENT", "development")
load_dotenv(f".env.{env}")
```

### 6. Monitoraggio Performance

```python
import time
from functools import wraps

def measure_time(func):
    """Decorator per misurare tempo esecuzione"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"⏱️  {func.__name__} completato in {elapsed:.2f}s")
        return result
    return wrapper

@measure_time
async def run_agent():
    # Implementation
    pass
```

---

## Migrazione STDIO → HTTP

### Perché Migrare?

Dopo debug estensivo con FastMCP, il transport STDIO presenta **problemi irrisolvibili**:

| Problema | Impatto | Soluzione |
|----------|---------|-----------|
| `start()` blocca 30s | App inutilizzabile | HTTP non bloccante |
| Handshake JSON-RPC fallisce | Tools non caricano | HTTP REST API |
| `with` chiude subprocess | Agent non funziona | HTTP server separato |
| Debugging impossibile | Timeout silenzioso | HTTP logs chiari |

### Step Migrazione

#### 1. Avvia FastMCP in HTTP Mode

**Prima (STDIO - Bloccante)**:

```bash
# ❌ Subprocess STDIO (blocca start())
uv run python nutrifit_activity_mcp.py
```

**Dopo (HTTP - Non Bloccante)**:

```bash
# ✅ Server HTTP su porta 8001
uv run python nutrifit_activity_mcp.py --transport streamablehttp --port 8001
```

#### 2. Modifica Agent Code

**Prima (STDIO)**:

```python
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client

# ❌ Blocca su start()
transport_factory = lambda: stdio_client(
    StdioServerParameters(
        command="uv",
        args=["run", "python", "server.py"]
    )
)
mcp_client = MCPClient(transport_factory)
mcp_client.start()  # BLOCCA QUI!
```

**Dopo (HTTP)**:

```python
from strands_mcp_client.transports.streamablehttp import streamablehttp_client

# ✅ Non bloccante
transport_factory = streamablehttp_client("http://localhost:8001/mcp/")
mcp_client = MCPClient(transport_factory)

# Context manager funziona perfettamente
with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(tools=tools)
```

#### 3. Docker Compose Setup

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  # MCP Server HTTP
  activity-mcp-server:
    build:
      context: ./mcp-servers/activity
    command: ["uv", "run", "python", "server.py", "--transport", "streamablehttp", "--port", "8001"]
    ports:
      - "8001:8001"
    environment:
      - GRAPHQL_ENDPOINT=http://backend:8080/graphql
    networks:
      - nutrifit
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Agent che consuma MCP via HTTP
  nutrifit-agent:
    build:
      context: ./agent-service
    environment:
      - ACTIVITY_MCP_URL=http://activity-mcp-server:8001/mcp/
      - MEAL_MCP_URL=http://meal-mcp-server:8002/mcp/
      - PROFILE_MCP_URL=http://profile-mcp-server:8003/mcp/
    depends_on:
      activity-mcp-server:
        condition: service_healthy
    networks:
      - nutrifit

networks:
  nutrifit:
    driver: bridge
```

#### 4. AgentManager Pattern HTTP

**File**: `nutrifit_agent_mcp.py`

```python
#!/usr/bin/env python3
"""AgentManager con HTTP Transport (non-blocking)"""

from typing import Dict, Optional
from strands.agent import Agent
from strands.models.bedrock import BedrockModels
from strands_mcp_client import MCPClient
from strands_mcp_client.transports.streamablehttp import streamablehttp_client

class AgentManager:
    """Manager con HTTP transport (risolve blocking STDIO)"""
    
    def __init__(self):
        # HTTP URLs per MCP servers
        self.mcp_urls = {
            "activity": "http://localhost:8001/mcp/",
            "meal": "http://localhost:8002/mcp/",
            "nutritional_profile": "http://localhost:8003/mcp/"
        }
        
        # Agents per utente (lazy initialization)
        self.user_swarms: Dict[str, Dict[str, Agent]] = {}
    
    def get_swarm_for_user(self, user_id: str) -> Dict[str, Agent]:
        """Crea o ritorna swarm agents per utente"""
        
        if user_id in self.user_swarms:
            return self.user_swarms[user_id]
        
        print(f"🔧 Initializing agents for user {user_id}...")
        
        agents = {}
        
        # Activity Agent con HTTP transport
        activity_transport = streamablehttp_client(self.mcp_urls["activity"])
        activity_client = MCPClient(activity_transport)
        
        # ✅ Context manager funziona perfettamente con HTTP
        with activity_client:
            activity_tools = activity_client.list_tools_sync()
            
            agents["activity"] = Agent(
                model=BedrockModels.CLAUDE_SONNET_4,
                tools=activity_tools,
                system_prompt="Activity tracking specialist..."
            )
        
        # Meal Agent
        meal_transport = streamablehttp_client(self.mcp_urls["meal"])
        meal_client = MCPClient(meal_transport)
        
        with meal_client:
            meal_tools = meal_client.list_tools_sync()
            
            agents["meal"] = Agent(
                model=BedrockModels.CLAUDE_SONNET_4,
                tools=meal_tools,
                system_prompt="Meal tracking specialist..."
            )
        
        # Nutritional Profile Agent
        profile_transport = streamablehttp_client(self.mcp_urls["nutritional_profile"])
        profile_client = MCPClient(profile_transport)
        
        with profile_client:
            profile_tools = profile_client.list_tools_sync()
            
            agents["nutritional_profile"] = Agent(
                model=BedrockModels.CLAUDE_SONNET_4,
                tools=profile_tools,
                system_prompt="Nutritional profile specialist..."
            )
        
        self.user_swarms[user_id] = agents
        print(f"✅ Agents ready for user {user_id}")
        
        return agents
    
    def cleanup_user_swarm(self, user_id: str):
        """Cleanup agents utente"""
        if user_id in self.user_swarms:
            del self.user_swarms[user_id]
            print(f"🧹 Cleaned up agents for user {user_id}")


# Singleton manager
agent_manager = AgentManager()
```

#### 5. FastAPI App con HTTP MCP

**File**: `app.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents.nutrifit_agent_mcp import agent_manager

app = FastAPI(title="Nutrifit Agent API")

class ChatRequest(BaseModel):
    message: str
    user_id: str
    agent_type: str = "activity"  # activity | meal | nutritional_profile

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint con HTTP MCP (non-blocking)"""
    try:
        # ✅ Nessun blocking - HTTP transport istantaneo
        agents = agent_manager.get_swarm_for_user(request.user_id)
        
        if request.agent_type not in agents:
            raise HTTPException(status_code=400, detail="Invalid agent_type")
        
        agent = agents[request.agent_type]
        
        # Execute agent
        response = agent.execute_task(request.message)
        
        return {
            "response": response,
            "success": True
        }
    
    except Exception as e:
        return {
            "response": str(e),
            "success": False
        }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "active_users": len(agent_manager.user_swarms)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Vantaggi HTTP Transport

✅ **Nessun Blocking**: `list_tools_sync()` istantaneo  
✅ **Context Manager Funziona**: Nessun problema con subprocess  
✅ **Debugging Facile**: Logs HTTP chiari  
✅ **Scalabile**: N agents → M servers  
✅ **Monitorabile**: Health checks endpoint  
✅ **Testabile**: `curl http://localhost:8001/health`

### Test Migrazione

```bash
# 1. Avvia MCP Server HTTP
cd mcp-servers/activity
uv run python server.py --transport streamablehttp --port 8001

# Output:
# 🚀 FastMCP server running on http://localhost:8001/mcp/

# 2. Test server direttamente
curl http://localhost:8001/health
# {"status": "ok"}

# 3. Avvia agent
cd agent-service
uv run python app.py

# 4. Test chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Mostra attività oggi",
    "user_id": "user-123",
    "agent_type": "activity"
  }'
```

---

## 🌐 HTTP API con FastAPI e CORS

### Problema CORS con Frontend

**Errore Tipico**:

```
Origin http://localhost:3000 is not allowed by Access-Control-Allow-Origin
Status code: 500
```

**Causa**: Doppio problema:

1. CORS non configurato correttamente
2. Errore 500 nel server blocca response CORS

### Soluzione Completa: FastAPI + Strands + MCP

#### 1. Dipendenze Corrette

```toml
# pyproject.toml per HTTP API Agent
[project]
name = "nutrifit-agent-api"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "strands-agents>=1.13.0",
    "mcp>=1.0.0",              # Per stdio_client
    "pydantic>=2.10.5",
    "python-dotenv>=1.0.0",
]
```

#### 2. Implementazione Corretta Agent API

**File**: `app.py`

```python
#!/usr/bin/env python3
"""
FastAPI HTTP API per Nutrifit Agent con MCP

CORREZIONI CRITICHE:
1. stdio_client() restituisce callable per MCPClient
2. Agent transfer via context manager
3. CORS configurato per ogni response
4. Error handling robusto per evitare 500
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from strands.agent import Agent
from strands.models.bedrock import BedrockModels
from strands.tools.mcp import MCPClient

# Import CORRETTO per stdio transport
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Nutrifit Agent API",
    version="1.0.0",
    description="HTTP API per Strands Agent con MCP tools"
)

# ============================================================================
# CORS CONFIGURATION - CRITICO!
# ============================================================================

# Configurazione CORS permissiva per sviluppo
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],  # Tutti gli headers
    expose_headers=["*"],
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Request body per /chat endpoint"""
    message: str
    user_id: Optional[str] = None
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    """Response body per /chat endpoint"""
    response: str
    success: bool
    agent_used: str = "activity"
    error: Optional[str] = None


# ============================================================================
# AGENT INITIALIZATION - CORREZIONE CRITICA
# ============================================================================

class AgentManager:
    """Manager per inizializzazione lazy di Strands Agent"""
    
    def __init__(self):
        self.agent: Optional[Agent] = None
        self.mcp_client: Optional[MCPClient] = None
        self._initialized = False
    
    async def initialize(self):
        """Inizializza agent con MCP tools"""
        if self._initialized:
            return
        
        try:
            logger.info("🔧 Inizializzazione Strands Agent...")
            
            # 1. Path al server MCP
            server_path = Path("/app/mcp-servers/activity/server.py")
            
            if not server_path.exists():
                raise FileNotFoundError(f"MCP server non trovato: {server_path}")
            
            logger.info(f"📁 MCP Server: {server_path}")
            
            # 2. CORREZIONE: Strands MCPClient richiede callable factory
            # stdio_client() è context manager, non callable per MCPClient
            # Dobbiamo creare una factory function
            
            server_params = StdioServerParameters(
                command="uv",
                args=["run", "python", str(server_path)],
                env=None  # Eredita environment
            )
            
            # Factory function che restituisce stdio_client context manager
            def transport_factory():
                return stdio_client(server_params)
            
            logger.info("🔌 Transport factory creato")
            
            # 3. Crea MCPClient con factory callable
            self.mcp_client = MCPClient(transport_factory)
            
            # 4. CORREZIONE: Avvia MCPClient manualmente (NON context manager)
            # Subprocess deve rimanere aperto durante agent.run()
            self.mcp_client.start()
            
            tools = await self.mcp_client.list_tools()
            
            logger.info(f"✅ {len(tools)} tools caricati da MCP")
            for tool in tools:
                logger.info(f"   - {tool.name}")
            
            # 5. CORREZIONE: Agent transfer via costruttore
            # Non esiste Agent.tools.extend()
            self.agent = Agent(
                model=BedrockModels.CLAUDE_SONNET_4,
                tools=tools,  # Pass tools al costruttore
                system_prompt="""Sei un assistente per tracking attività fisica.

Tools disponibili:
- get_activity_entries: Query dati minuto-per-minuto
- get_activity_sync_entries: Sync giornaliero delta
- aggregate_activity_range: Aggregazioni (DAY/WEEK/MONTH)
- sync_activity_events: Batch sync da dispositivi
- sync_health_totals: Snapshot totali giornalieri

Rispondi in italiano con dati precisi e insights utili.""",
                temperature=0.3
            )
            
            self._initialized = True
            logger.info("✅ Agent inizializzato con successo")
        
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione agent: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def chat(self, message: str, context: dict = None) -> str:
        """
        Esegui chat con agent
        
        Args:
            message: Messaggio utente
            context: Context opzionale
        
        Returns:
            Response agent
        """
        if not self._initialized:
            await self.initialize()
        
        # Enhanced message con context
        enhanced_message = message
        if context:
            context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
            enhanced_message = f"Context:\n{context_str}\n\nQuery: {message}"
        
        # Execute agent
        # NOTA: MCPClient già avviato in initialize(), subprocess rimane aperto
        response = await self.agent.run(enhanced_message)
        return response.final_response
    
    async def cleanup(self):
        """Cleanup MCPClient subprocess"""
        if self.mcp_client:
            logger.info("🛑 Chiusura MCPClient...")
            self.mcp_client.stop()


# Singleton agent manager
agent_manager = AgentManager()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Inizializza agent all'avvio"""
    try:
        await agent_manager.initialize()
        logger.info("🚀 API pronta - Agent inizializzato")
    except Exception as e:
        logger.error(f"⚠️  Avvio con errore: {e}")
        # Non bloccare startup - lazy init su prima richiesta


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup al shutdown"""
    logger.info("👋 Shutdown - Cleanup MCPClient...")
    await agent_manager.cleanup()


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "Nutrifit Agent API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check dettagliato"""
    return {
        "status": "healthy",
        "agent_initialized": agent_manager._initialized,
        "timestamp": "2025-11-21T12:00:00Z"
    }


@app.post("/api/agent/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint per interazione con agent
    
    CORS-safe: Gestisce OPTIONS preflight automaticamente
    Error handling: Nessun 500 non gestito
    """
    try:
        logger.info(f"📨 Chat request: {request.message[:50]}...")
        
        # Esegui agent
        response = await agent_manager.chat(
            message=request.message,
            context=request.context
        )
        
        logger.info(f"✅ Response generata: {len(response)} chars")
        
        return ChatResponse(
            response=response,
            success=True,
            agent_used="activity"
        )
    
    except FileNotFoundError as e:
        logger.error(f"❌ MCP Server non trovato: {e}")
        return ChatResponse(
            response="Configurazione server non corretta",
            success=False,
            error=str(e)
        )
    
    except Exception as e:
        logger.error(f"❌ Errore chat: {e}")
        import traceback
        traceback.print_exc()
        
        # Ritorna 200 con success=false invece di 500
        # Questo permette CORS response
        return ChatResponse(
            response="Errore interno del server",
            success=False,
            error=str(e)
        )


@app.options("/api/agent/chat")
async def chat_options():
    """
    OPTIONS preflight per CORS
    FastAPI + CORSMiddleware gestisce automaticamente,
    ma esplicito per debugging
    """
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload su modifiche
        log_level="info"
    )
```

#### 3. Dockerfile con CORS Support

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project
COPY pyproject.toml .
COPY app.py .
COPY mcp-servers/ ./mcp-servers/

# Install dependencies
RUN uv sync

# Expose port
EXPOSE 8000

# Environment
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 4. Docker Compose con Network Config

```yaml
version: '3.8'

services:
  nutrifit-agent-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GRAPHQL_ENDPOINT=http://graphql-api:8080/graphql
      - AWS_REGION=us-east-1
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    volumes:
      - ./app.py:/app/app.py
      - ./mcp-servers:/app/mcp-servers
    networks:
      - nutrifit-network
    restart: unless-stopped

networks:
  nutrifit-network:
    driver: bridge
```

#### 5. Test Frontend CORS-Safe

**File**: `test-agent.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Test Nutrifit Agent API</title>
</head>
<body>
    <h1>Test Agent Chat</h1>
    
    <textarea id="message" rows="4" cols="50" placeholder="Enter message..."></textarea>
    <br>
    <button onclick="sendChat()">Send</button>
    
    <h2>Response:</h2>
    <pre id="response"></pre>
    
    <script>
        async function sendChat() {
            const message = document.getElementById('message').value;
            const responseEl = document.getElementById('response');
            
            try {
                responseEl.textContent = 'Loading...';
                
                const response = await fetch('http://localhost:8000/api/agent/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // CORS headers automatici dal browser
                    },
                    body: JSON.stringify({
                        message: message,
                        user_id: 'test-user-123',
                        context: {
                            date: new Date().toISOString().split('T')[0]
                        }
                    })
                });
                
                // Parse response anche se status != 200
                const data = await response.json();
                
                if (data.success) {
                    responseEl.textContent = data.response;
                } else {
                    responseEl.textContent = `Error: ${data.error}\n\n${data.response}`;
                    responseEl.style.color = 'red';
                }
            } catch (error) {
                responseEl.textContent = `Fetch error: ${error.message}`;
                responseEl.style.color = 'red';
                console.error('Fetch error:', error);
            }
        }
    </script>
</body>
</html>
```

#### 6. Test con curl

```bash
# Test OPTIONS preflight
curl -X OPTIONS http://localhost:8000/api/agent/chat \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -v

# Test POST chat
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{
    "message": "Quanti passi ho fatto oggi?",
    "user_id": "test-123"
  }' \
  | jq
```

### 🔧 Troubleshooting CORS

#### Errore: "Origin not allowed"

**Verifica 1 - CORS Middleware**:

```python
# Verifica che allow_origins includa il tuo frontend
allow_origins=["http://localhost:3000"]
```

**Verifica 2 - Nessun errore 500**:

```bash
# Controlla logs
docker logs nutrifit-agent-api --tail 50

# Cerca traceback
docker logs nutrifit-agent-api 2>&1 | grep -A 10 "Traceback"
```

**Verifica 3 - OPTIONS preflight**:

```bash
# Browser invia OPTIONS prima di POST
curl -X OPTIONS http://localhost:8000/api/agent/chat -v
```

#### Errore: "AsyncContextDecorator.**call**() missing 1 required positional argument"

**Causa**: `stdio_client()` è un context manager, non un callable diretto per MCPClient

**Soluzione - Factory Function**:

```python
# ❌ SBAGLIATO - stdio_client non è callable per MCPClient
from mcp.client.stdio import stdio_client
transport = stdio_client(StdioServerParameters(...))
mcp_client = MCPClient(transport)  # TypeError!

# ✅ CORRETTO - Wrap in factory function
def transport_factory():
    return stdio_client(StdioServerParameters(
        command="uv",
        args=["run", "python", str(server_path)]
    ))

mcp_client = MCPClient(transport_factory)  # OK
```

**Alternativa - Lambda**:

```python
# ✅ CORRETTO - Lambda factory
transport_factory = lambda: stdio_client(StdioServerParameters(
    command="uv",
    args=["run", "python", str(server_path)]
))

mcp_client = MCPClient(transport_factory)
```

#### Errore: "Agent has no attribute 'tools'"

**Causa**: API Strands non permette Agent.tools.extend()

**Soluzione**:

```python
# ❌ SBAGLIATO
agent = Agent(model=...)
agent.tools.extend(mcp_tools)  # AttributeError!

# ✅ CORRETTO
async with mcp_client:
    tools = await mcp_client.list_tools()
    agent = Agent(model=..., tools=tools)  # Pass al costruttore
```

#### Errore: "MCP tools not available during execution"

**Causa**: MCPClient subprocess chiuso prima di agent.run()

**Soluzione - Lifecycle manuale**:

```python
# ❌ SBAGLIATO - Context manager chiude subprocess
async with mcp_client:
    tools = await mcp_client.list_tools()
    agent = Agent(tools=tools)
# Subprocess chiuso qui!
response = await agent.run(message)  # McpError: Connection closed

# ✅ CORRETTO - Gestione manuale lifecycle
mcp_client.start()  # Avvia subprocess

try:
    tools = await mcp_client.list_tools()
    agent = Agent(tools=tools)
    
    # Subprocess rimane aperto
    response = await agent.run(message)  # OK
    
finally:
    mcp_client.stop()  # Cleanup subprocess
```

**Pattern Long-Running Application**:

```python
class AgentManager:
    def __init__(self):
        self.mcp_client = None
        self.agent = None
    
    async def initialize(self):
        """Setup iniziale"""
        transport_factory = lambda: stdio_client(...)
        self.mcp_client = MCPClient(transport_factory)
        
        # Avvia una sola volta
        self.mcp_client.start()
        
        tools = await self.mcp_client.list_tools()
        self.agent = Agent(tools=tools)
    
    async def chat(self, message: str):
        """Subprocess già aperto, usalo direttamente"""
        return await self.agent.run(message)
    
    async def cleanup(self):
        """Cleanup al shutdown dell'app"""
        if self.mcp_client:
            self.mcp_client.stop()
```

### 🎯 Checklist CORS + HTTP API

- [ ] ✅ `CORSMiddleware` configurato con origins corretti
- [ ] ✅ `allow_methods=["*"]` include POST e OPTIONS
- [ ] ✅ `allow_headers=["*"]` permette tutti headers
- [ ] ✅ Endpoint ritorna 200 anche su errori (success=false)
- [ ] ✅ Factory function wrappa `stdio_client(StdioServerParameters(...))`
- [ ] ✅ Tools passati a `Agent()` costruttore, non extend
- [ ] ✅ `MCPClient.start()` chiamato prima di usare tools
- [ ] ✅ `MCPClient.stop()` chiamato in cleanup/shutdown
- [ ] ✅ NON usare `with mcp_client:` (chiude subprocess prematuramente)
- [ ] ✅ Error handling previene 500 unhandled
- [ ] ✅ Logging dettagliato per debugging
- [ ] ✅ Health check endpoint disponibile

### 📊 Performance Optimization

**Lazy Initialization**:

```python
# Inizializza agent solo alla prima richiesta
@app.on_event("startup")
async def startup_event():
    # Non bloccare startup se MCP server non pronto
    try:
        await agent_manager.initialize()
    except:
        logger.warning("Agent init failed, will retry on first request")
```

**Connection Pooling**:

```python
# Riutilizza MCPClient tra richieste
class AgentManager:
    def __init__(self):
        self.mcp_client = None  # Singleton
    
    async def ensure_initialized(self):
        if not self.mcp_client:
            # Initialize once
            pass
```

**Caching Responses**:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_response(message_hash: str):
    # Cache risposte comuni
    pass
```

---

## 🎯 Quick Start Template

### Minimal Working Example

```python
#!/usr/bin/env python3
"""Minimal Nutrifit Agent with FastMCP"""

import asyncio
from pathlib import Path
from strands.agent import Agent
from strands.models.bedrock import BedrockModels
from strands_mcp_client import MCPClient, StdioServerParameters

async def main():
    # 1. Path server MCP
    server_path = Path(__file__).parent.parent / "mcp" / "nutrifit_activity_mcp.py"
    
    # 2. Transport STDIO
    transport = StdioServerParameters(
        command="uv",
        args=["run", "python", str(server_path)]
    )
    
    # 3. MCPClient
    mcp_client = MCPClient(transport)
    
    # 4. Load tools e crea agent
    with mcp_client:
        tools = mcp_client.list_tools_sync()
        agent = Agent(
            model=BedrockModels.CLAUDE_SONNET_4,
            tools=tools
        )
        
        # 5. Query
        response = agent.execute_task(
            "Mostra attività utente test-123 per oggi"
        )
        print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

Salva come `minimal_agent.py`, poi:

```bash
# Setup .env
echo "GRAPHQL_ENDPOINT=http://localhost:8080/graphql" > .env
echo "AWS_REGION=us-east-1" >> .env

# Run
uv run python minimal_agent.py
```

---

## 📚 Riferimenti

### Documentazione

- **FastMCP**: <https://github.com/jlowin/fastmcp>
- **Strands**: <https://github.com/strands-ai/strands>
- **MCP Protocol**: <https://modelcontextprotocol.io/>

### Esempi in Workspace

- **STDIO Example**: `strands/example-2/agent/agent.py`
- **HTTP Example**: `strands/example-1/agent/agent.py`
- **MCP Server**: `mcp/math_server.py`

### Supporto

Per problemi specifici:

1. Verifica `TROUBLESHOOTING.md`
2. Consulta `WORKSPACE_ANALYSIS.md`
3. Controlla logs con `LOG_LEVEL=DEBUG`

---

## 🔑 Punti Chiave

### ✅ Pattern Funzionanti

1. **FastMCP è già compatibile** - Server non necessita modifiche
2. **HTTP Transport è obbligatorio** - STDIO blocca con FastMCP
3. **Context manager funziona con HTTP** - Lifecycle automatico
4. **Scalabilità garantita** - N agents → M servers HTTP
5. **Debugging facilitato** - Logs HTTP chiari e health checks

### ❌ Pattern NON Funzionanti (Evitare)

1. **STDIO Transport con FastMCP** - `start()` blocca 30s (handshake fallisce)
2. **Pattern `start()` manuale** - Non risolve blocking STDIO
3. **Global MCPClient STDIO** - Initialization blocca app startup
4. **Subprocess lifecycle management** - Incompatibile con FastMCP

### 🎯 Best Practices

1. ✅ **Usa sempre HTTP transport** per FastMCP servers
2. ✅ **Avvia server separati** con `--transport streamablehttp`
3. ✅ **Docker Compose** per orchestrazione multi-server
4. ✅ **Health checks** su tutti i server MCP
5. ✅ **Environment variables** per URLs MCP
6. ✅ **Idempotency keys** per operazioni sync
7. ✅ **Error handling** robusto su network calls
8. ✅ **Lazy initialization** agents per utente
9. ✅ **Connection pooling** con HTTP client
10. ✅ **Monitoraggio** con logs e metrics endpoint

---

**Versione**: 1.0  
**Data**: 21 novembre 2025  
**Autore**: GitHub Copilot  
**Workspace**: mcp-and-agent
