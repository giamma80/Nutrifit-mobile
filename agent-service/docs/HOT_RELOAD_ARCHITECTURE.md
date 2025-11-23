# Hot-Reload Architecture for MCP Tools

## Problema

Durante lo sviluppo, modifiche ai tool MCP (nuove funzioni, firme modificate, descrizioni aggiornate) non venivano riflesse in agent-service senza restart manuale del container.

## Soluzione Multi-Livello

### 1. Cache TTL (Automatic Expiration)

**Scopo**: Refresh graduale in produzione  
**Timeout**: 3600 secondi (1 ora) - configurabile

```python
class NutrifitAgentManager:
    def __init__(self):
        self.swarm_ttl = 3600  # 1 hour cache
        self.swarms = {}  # {user_id: {"swarm": Swarm, "created_at": timestamp}}
```

**Funzionamento**:

1. Ad ogni richiesta, check età dello swarm
2. Se `age >= swarm_ttl` → delete cache entry
3. Tools ricaricati da HTTP MCP servers
4. Nuovo swarm creato con tools aggiornati

**Vantaggio**: Zero downtime, refresh automatico senza intervento

---

### 2. Manual Invalidation (On Server Stop)

**Scopo**: Immediate refresh durante sviluppo/restart  
**Trigger**: `stop_mcp_servers()` chiamato da lifespan shutdown

```python
def stop_mcp_servers(self):
    # ... terminate processes ...
    self.mcp_processes.clear()
    self.mcp_server_pids.clear()
    self.swarms.clear()  # ← Force reload
```

**Workflow Development**:

1. Modifica codice MCP tool
2. `docker restart nutrifit-agent`
3. Lifespan shutdown → `stop_mcp_servers()`
4. Cache cleared automatically
5. Next request loads fresh tools

**Vantaggio**: Immediate reflection di modifiche senza attesa TTL

---

### 3. PID Monitoring (Runtime Detection)

**Scopo**: Detect restart automatico server MCP (crash/restart esterno)  
**Check**: Ad ogni `get_swarm_for_user()` verifica PIDs

```python
def _check_servers_alive(self) -> bool:
    for server_name, expected_pid in self.mcp_server_pids.items():
        process = self.mcp_processes.get(server_name)
        
        # Check process died
        if process.poll() is not None:
            return False
        
        # Check PID changed (external restart)
        if process.pid != expected_pid:
            return False
    
    return True
```

**Funzionamento**:

1. Startup: Store PID di ogni subprocess MCP
2. Ogni request user: Check PIDs attuali vs stored
3. Se mismatch → `self.swarms.clear()`
4. Tools ricaricati da nuovi processi

**Scenari Protetti**:

- MCP subprocess crasha → detectato
- Supervisor/orchestrator restarta MCP → detectato
- Health check esterno restarta MCP → detectato

**Vantaggio**: Zero manualità, auto-recovery da crash

---

## Architettura Completa

```
┌─────────────────────────────────────────────────────────────┐
│ agent_manager.get_swarm_for_user(user_id, token)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────┐
         │ _check_servers_alive()             │
         │ PIDs match stored?                 │
         └────────────────────────────────────┘
                  │                    │
            NO ───┘                    └─── YES
            │                               │
            ▼                               ▼
  ┌──────────────────┐         ┌─────────────────────┐
  │ swarms.clear()   │         │ Check TTL:          │
  │ [PID changed]    │         │ age < swarm_ttl?    │
  └──────────────────┘         └─────────────────────┘
            │                    │              │
            │               NO ──┘              └── YES
            │               │                        │
            └───────────────┴───> RELOAD         CACHE HIT
                            │                        │
                            ▼                        ▼
              ┌──────────────────────────┐   ┌──────────────┐
              │ Load tools from HTTP:    │   │ Return       │
              │ - user (8004)            │   │ cached swarm │
              │ - meal (8001)            │   └──────────────┘
              │ - activity (8002)        │
              │ - nutritional_profile    │
              │   (8003)                 │
              │                          │
              │ Create new Swarm         │
              │ Store with timestamp     │
              └──────────────────────────┘
```

---

## Configurazione

### Produzione (Default)

```python
self.swarm_ttl = 3600  # 1 hour
```

**Caratteristiche**:

- Carico ridotto su MCP servers
- Tool loading ogni ora max
- PID monitoring protegge da crash

### Development (Fast Iteration)

```python
self.swarm_ttl = 60  # 1 minute
```

**Caratteristiche**:

- Modifiche visibili entro 1 minuto
- No restart required
- - PID monitoring per restart immediato

### Testing (No Cache)

```python
self.swarm_ttl = 0  # Disable cache
```

**Caratteristiche**:

- Tools sempre ricaricati
- Testing tool signatures
- Performance impact acceptable in test

---

## Logging

### Cache Hit

```
♻️  Reusing existing Swarm for user abc123 (age: 45s)
```

### Cache Expiration

```
🔄 Swarm expired for user abc123 (age: 3610s), reloading tools...
📥 Loading tools from meal (http://localhost:8001)...
✅ Loaded 15 tools from meal
```

### PID Detection

```
⚠️  meal PID changed (12345 → 12567)
🔄 MCP servers changed, invalidating all swarms...
```

### Manual Invalidation

```
🛑 Stopping HTTP MCP servers...
🔄 Invalidating all cached swarms...
✅ All MCP servers stopped and cache cleared
```

---

## Metriche

### Cache Hit Rate

Monitor `swarms.get(user_id)` hits vs misses per ottimizzare TTL

### Tool Loading Time

Monitor tempo `_load_tools_from_server()` per detectare problemi HTTP

### PID Changes

Count PID mismatches per detectare instabilità MCP servers

---

## Testing

### Test Manuale

```bash
# 1. Start agent-service
docker-compose up agent-service

# 2. Create swarm (primo caricamento)
curl -X POST http://localhost:8080/api/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "ciao"}'

# 3. Modifica MCP tool (es: meal-mcp/server_fastmcp.py)

# 4. Restart container
docker restart nutrifit-agent

# 5. Verifica tool aggiornato
curl -X POST http://localhost:8080/api/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "usa il nuovo tool"}'
```

### Test Automatico

```bash
# Run PID monitoring test
docker exec -it nutrifit-agent python test_pid_monitoring.py
```

---

## Troubleshooting

### Tools non aggiornati dopo restart

**Sintomo**: Modifiche a MCP non visibili  
**Cause**:

1. Cache TTL non scaduto → Attendi o riavvia
2. PID check disabled → Check `_check_servers_alive()` called
3. HTTP server non riavviato → Check MCP subprocess logs

**Fix**:

```python
# Force immediate reload
agent_manager.swarms.clear()
```

### PID check troppo aggressivo

**Sintomo**: Cache cleared troppo spesso  
**Cause**: False positive su PID checks

**Fix**:

```python
# Add retry logic to _check_servers_alive()
if not self._check_servers_alive():
    await asyncio.sleep(0.5)  # Wait for process stabilization
    if not self._check_servers_alive():  # Confirm
        self.swarms.clear()
```

### Performance degradation

**Sintomo**: Slow response dopo TTL expiration  
**Cause**: Tool loading blocking

**Fix**:

```python
# Preload tools in background
asyncio.create_task(self._load_tools_from_server(...))
```

---

## Conclusioni

Architettura hot-reload a 3 livelli:

1. **TTL Cache** (3600s): Automatic gradual refresh
2. **Manual Invalidation**: Immediate on restart
3. **PID Monitoring**: Auto-detect crashes/restarts

**Risultato**: Zero-downtime development con reflection automatica modifiche MCP tools.
