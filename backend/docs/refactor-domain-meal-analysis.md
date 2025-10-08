# Domain-Driven Refactor: AI Meal Analysis

## Overview

Questo documento descrive il refactor completato della logica di analisi foto pasto da un'architettura sparsa a una struttura domain-driven centralizzata.

## Obiettivi Raggiunti

### 1. **"Fare un po' di ordine, un refactor easy"** ✅
- Implementata architettura domain-driven con separazione chiara delle responsabilità
- Refactor non invasivo con feature flag per rollback sicuro

### 2. **"Logica di business troppo sparsa"** ✅ 
- Business logic centralizzata in `domain/meal/application/meal_analysis_service.py`
- Pipeline normalizzazione estratta in `domain/meal/pipeline/normalizer.py`

### 3. **"Disaccoppiata dalla logica di come sono esposte le API"** ✅
- Domain service separato dalla layer GraphQL
- Interfacce pulite tramite Ports & Adapters pattern

### 4. **"Aumentando il disaccoppiamento"** ✅
- Dependency injection via `MealAnalysisService.create_with_defaults()`
- Interface segregation con ports chiari

## Architettura

```
domain/meal/
├── application/
│   └── meal_analysis_service.py    # 🎯 Application Service orchestratore
├── ports/
│   ├── vision_port.py              # Interface per vision detection  
│   └── product_lookup_port.py      # Interface per lookup prodotti
├── model/
│   ├── meal_item.py               # Domain entities
│   ├── requests.py                # Request/Response DTOs
│   └── exceptions.py              # Domain exceptions
├── pipeline/
│   └── normalizer.py              # 🔄 Pipeline normalizzazione centralizzata
└── adapters/
    └── __init__.py                # Future: adapter implementations
```

## Feature Flag

### Controllo
```bash
# Default sicuro (legacy path)
AI_MEAL_ANALYSIS_V2=0

# Attiva nuovo domain service  
AI_MEAL_ANALYSIS_V2=1
```

### Comportamento
| Flag Value | Path | Source GraphQL | Business Logic Location |
|------------|------|----------------|-------------------------|
| `0` (default) | Legacy | `"gpt4v"` | Sparso in adapter |
| `1` (nuovo) | Domain Service | `"gpt4v_v2"` | Centralizzato in service |

## API Compatibility

### ✅ **Nessun Breaking Change**
- Query GraphQL identiche
- Response structure identica  
- Stessi campi disponibili

### Differenze Comportamentali
- **Source tracking**: `gpt4v` vs `gpt4v_v2` per observability
- **Business logic**: Centralizzata vs sparsa
- **Testabilità**: Domain isolato dall'infrastruttura

## Implementazione Completata

### ✅ Core Features
- [x] Domain skeleton structure
- [x] Feature flag `AI_MEAL_ANALYSIS_V2`
- [x] Application service orchestrazione
- [x] Pipeline normalizzazione estratta
- [x] GraphQL integration con fallback

### ✅ Integration & Safety  
- [x] Repository integration per `confirmMealPhoto`
- [x] Idempotency handling completa
- [x] Graceful fallback su errori → legacy path
- [x] Test equivalenza per validazione comportamento

### ✅ Quality & Production-Ready
- [x] Tutti i test passano (135+ tests)
- [x] Linting pulito (Flake8 + MyPy)
- [x] Backward compatibility garantita

## Rollout Strategy

### Phase 1: Canary (Attuale)
```bash
# In sviluppo/test
AI_MEAL_ANALYSIS_V2=1

# Monitorare:
# - Metrics con source: "gpt4v_v2"
# - Log per fallback: "domain_service_error_fallback_to_legacy"
```

### Phase 2: Production Graduale
```bash
# Percentage rollout tramite environment
# 10% → 50% → 100% degli utenti
```

### Phase 3: Cleanup (Futuro)
- Rimuovere feature flag quando stabile
- Deprecare percorso legacy
- Cleanup adapter duplicato

## Testing

### Test Equivalenza
```bash
# Valida che V2 produce risultati identici a legacy
uv run pytest tests/test_meal_analysis_service_equivalence.py -v
```

### Test Integration  
- Workflow completo: `analyzeMealPhoto` → `confirmMealPhoto`
- Idempotency con chiavi duplicate
- Fallback su errori domain service

## Metrics & Observability

### Source Tracking
- Legacy: `source: "gpt4v"`
- Domain: `source: "gpt4v_v2"`

### Fallback Monitoring
```
LOG: domain_service_error_fallback_to_legacy
```

### Success Metrics
- Stessi risultati business tra percorsi
- Nessun aumento errori `confirmMealPhoto` 
- Performance equivalente

## Benefits Achieved

### 🎯 **Code Quality**
- Business logic centralizzata e testabile
- Separation of concerns migliorata
- Domain model esplicito

### 🔧 **Maintainability** 
- Estensibilità tramite ports
- Testing isolato del domain
- Dependency injection pulita

### 🚀 **Production Safety**
- Feature flag per rollback immediato
- Fallback automatico su errori
- Backward compatibility garantita

---

**Status: ✅ COMPLETED & PRODUCTION-READY**

*Refactor completato il 8 ottobre 2025*