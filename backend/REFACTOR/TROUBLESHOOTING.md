# 🔧 Troubleshooting - FAQ Essenziali

**Data:** 23 Ottobre 2025  
**Versione:** 1.0 (Minimale)  
**Status:** Top 5 Critical Issues Only

---

## 🎯 Quando Usare Questa Guida

**Scenario**: Errore in produzione o sviluppo che blocca il lavoro.  
**Obiettivo**: Fix rapido (< 5 minuti) per i 5 problemi più comuni.

Per troubleshooting completo, consulta la documentazione specifica in:
- OpenAI issues → `04_INFRASTRUCTURE_LAYER.md`
- Test failures → `05_TESTING_STRATEGY.md`
- Deployment problems → `08_DEPLOYMENT.md`

---

## 🚨 Top 5 Critical Issues

### 1. ❌ OpenAI Rate Limit (429 Error)

**Errore**:
```python
openai.RateLimitError: Error code: 429 - Rate limit reached
```

**Fix Rapido**:
```python
# infrastructure/openai/client.py
@retry(
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(5)
)
```

**Verifica**:
```bash
curl https://status.openai.com/api/v2/summary.json
```

---

### 2. ❌ "Event loop is closed" nei Test

**Errore**:
```python
RuntimeError: Event loop is closed
```

**Fix Rapido**:
```python
# conftest.py
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

**Verifica**: `pytest tests/ -v` (zero RuntimeError)

---

### 3. ❌ Circuit Breaker Sempre Aperto

**Errore**:
```
All requests fail: Circuit breaker OPEN
```

**Fix Rapido**:
```bash
# 1. Verifica API esterna
curl https://status.openai.com/api/v2/summary.json

# 2. Reset manuale (emergenza)
from infrastructure.resilience import openai_breaker
openai_breaker.reset()
```

**Verifica**: `GET /health` → status 200

---

### 4. ❌ USDA Returns 500 Results (Too Vague)

**Errore**:
```
USDA query "chicken" → 500 results, user confused
```

**Fix Rapido**:
```python
# infrastructure/openai/prompt.py
USDA LABEL RULES:
- ✅ "chicken breast, raw" (precise)
- ❌ "chicken" (too vague)

# infrastructure/usda/client.py
params = {
    "query": query,
    "dataType": ["SR Legacy"],  # High-quality only
    "pageSize": 25  # Limit results
}
```

**Verifica**: Test con "pasta" → max 25 results, SR Legacy prioritized

---

### 5. ❌ Redis Cache Not Working

**Errore**:
```
Cache hit rate: 0%, costs high
```

**Fix Rapido**:
```bash
# 1. Verifica Redis
redis-cli PING  # Should return PONG

# 2. Check cache keys
redis-cli KEYS "usda:search:*"

# 3. Test cache manually
redis-cli SET "test:key" "test:value" EX 60
redis-cli GET "test:key"  # Should return "test:value"
```

**Verifica**:
```python
# Log cache hits
logger.info(f"Cache hit rate: {hit_rate:.1%}")  # Should be >50%
```

---

## 📞 Escalation Path

| Severity | Action | Response Time |
|----------|--------|---------------|
| **P0** (Produzione Down) | Slack #backend-oncall | <15 min |
| **P1** (Feature Broken) | Slack #backend-alerts | <2h |
| **P2** (Performance Degraded) | GitHub Issue | Next business day |
| **P3** (Minor Bug) | Add to backlog | Weekly review |

---

## 🔍 Quick Diagnostics

```bash
# Health check completo
make health-check

# Test suite
make test

# Lint & Type check
make lint

# Log recenti (produzione)
render logs --tail 100
```

---

**Last Updated**: 23 Ottobre 2025  
**Maintainer**: Development Team
