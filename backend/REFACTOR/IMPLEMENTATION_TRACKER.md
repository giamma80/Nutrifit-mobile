# 🎯 Nutrifit Meal Domain Refactor - Implementation Tracker

**Version:** 2.0  
**Date:** 22 Ottobre 2025  
**Branch:** `refactor`  
**Status:** 🟡 In Progress

---

## 📊 Progress Overview

| Phase | Tasks | Completed | In Progress | Blocked | Not Started |
|-------|-------|-----------|-------------|---------|-------------|
| **Phase 0** | 4 | 4 | 0 | 0 | 0 |
| **Phase 1** | 5 | 2 | 0 | 0 | 3 |
| **Phase 2** | 3 | 0 | 0 | 0 | 3 |
| **Phase 3** | 7 | 0 | 0 | 0 | 7 |
| **Phase 4** | 4 | 0 | 0 | 0 | 4 |
| **Phase 5** | 4 | 0 | 0 | 0 | 4 |
| **Phase 6** | 3 | 0 | 0 | 0 | 3 |
| **Phase 7** | 2 | 0 | 0 | 0 | 2 |
| **TOTAL** | **32** | **6** | **0** | **0** | **26** |

---

## 📋 Phase 0: Cleanup & Preparation (3-4 ore)

**Goal:** Preparare workspace preservando client esterni funzionanti + upgrade dependencies.

| ID | Task | Description | Reference Doc | Expected Result | Status | Notes |
|----|------|-------------|---------------|-----------------|--------|-------|
| **P0.1** | **Upgrade OpenAI Dependencies** | Aggiornare `pyproject.toml` con OpenAI 2.5.0+, circuitbreaker, tenacity | `01_IMPLEMENTATION_GUIDE.md` §95-130 | `openai==^2.5.0`, `circuitbreaker==^1.4.0`, `tenacity==^8.2.0` installati e verificati | 🟢 COMPLETED | OpenAI 2.6.0 installed successfully |
| P0.1.1 | Modifica pyproject.toml | Aggiornare dependencies in `[project.dependencies]` | `01_IMPLEMENTATION_GUIDE.md` §104-113 | File `pyproject.toml` modificato | 🟢 COMPLETED | Added: openai >=2.5.0, pydantic >=2.0.0, circuitbreaker, tenacity, ruff, pytest-cov |
| P0.1.2 | Installa dipendenze | Eseguire `uv sync` | `01_IMPLEMENTATION_GUIDE.md` §115-117 | Dipendenze installate, `uv.lock` aggiornato | 🟢 COMPLETED | All packages installed |
| P0.1.3 | Verifica OpenAI version | Eseguire `uv run python -c "import openai; print(openai.__version__)"` | `01_IMPLEMENTATION_GUIDE.md` §119-121 | Output: `2.5.0` o superiore | 🟢 COMPLETED | OpenAI 2.6.0 verified |
| P0.1.4 | Verifica nuove dipendenze | Eseguire test import circuitbreaker e tenacity | `01_IMPLEMENTATION_GUIDE.md` §123-124 | Output: `✓ OK` | 🟢 COMPLETED | All imports successful |
| P0.1.5 | Commit upgrade | `git commit -m "build(deps): upgrade openai to 2.5.0+ for structured outputs"` | `01_IMPLEMENTATION_GUIDE.md` §126-130 | Commit creato e pushato | 🟢 COMPLETED | Commit f860b4d |
| **P0.2** | **Analyze Dependencies** | Identificare tutti gli import di vecchio codice meal domain | `01_IMPLEMENTATION_GUIDE.md` §135-139 | Lista completa dipendenze identificate | 🟢 COMPLETED | Found old domain/meal + clients to preserve |
| P0.2.1 | Find domain imports | `grep -r "from backend.domain.meal" backend/ --include="*.py"` | `01_IMPLEMENTATION_GUIDE.md` §137 | Lista file che importano domain.meal | 🟢 COMPLETED | Found: graphql/meal_resolver.py, app.py, tests/* |
| P0.2.2 | Find GraphQL imports | `grep -r "from backend.graphql.meal" backend/ --include="*.py"` | `01_IMPLEMENTATION_GUIDE.md` §138 | Lista file che importano graphql.meal | 🟢 COMPLETED | No imports found (flat structure) |
| **P0.3** | **Selective Cleanup** | Rimuovere architettura obsoleta preservando client esterni | `01_IMPLEMENTATION_GUIDE.md` §141-163 | Domain meal pulito, client esterni preservati | 🟢 COMPLETED | 38 files removed, clients preserved |
| P0.3.1 | Remove domain folders | Rimuovere cartelle obsolete in `backend/domain/meal/` | `01_IMPLEMENTATION_GUIDE.md` §145-149 | Cartelle `adapters/`, `application/`, `entities/`, etc. rimosse | 🟢 COMPLETED | Removed entire backend/domain/meal/ |
| P0.3.2 | Remove domain files | Rimuovere file obsoleti (`errors.py`, `integration.py`, etc.) | `01_IMPLEMENTATION_GUIDE.md` §149 | File obsoleti rimossi | 🟢 COMPLETED | All old domain files removed |
| P0.3.3 | Remove GraphQL resolvers | Rimuovere `meal_resolver.py` e `types_meal.py` | `01_IMPLEMENTATION_GUIDE.md` §151-153 | File GraphQL vecchi rimossi | 🟢 COMPLETED | Removed meal_resolver.py + types_meal.py |
| P0.3.4 | Commit cleanup | `git commit -m "refactor(meal): selective cleanup - preserve external clients"` | `01_IMPLEMENTATION_GUIDE.md` §155-158 | Commit cleanup creato | 🟢 COMPLETED | Commit fba58cf (BREAKING CHANGE) |
| **P0.4** | **Create New Structure** | Creare struttura cartelle per nuova architettura | `01_IMPLEMENTATION_GUIDE.md` §165-181 | Struttura completa domain/application/infrastructure/tests | 🟢 COMPLETED | 75 directories + __init__.py created, commit 78b4930 |
| P0.4.1 | Create domain structure | `mkdir -p backend/domain/meal/{nutrition,recognition,barcode,core}/...` | `01_IMPLEMENTATION_GUIDE.md` §167-169 | Cartelle domain create | 🟢 COMPLETED | Created with capabilities structure |
| P0.4.2 | Create application structure | `mkdir -p backend/application/meal/{commands,queries,orchestrators,...}` | `01_IMPLEMENTATION_GUIDE.md` §171-172 | Cartelle application create | 🟢 COMPLETED | Created CQRS structure |
| P0.4.3 | Create infrastructure structure | `mkdir -p backend/infrastructure/{ai,external_apis,persistence,...}` | `01_IMPLEMENTATION_GUIDE.md` §174-175 | Cartelle infrastructure create | 🟢 COMPLETED | Created adapters structure |
| P0.4.4 | Create GraphQL structure | `mkdir -p backend/graphql/resolvers/meal` | `01_IMPLEMENTATION_GUIDE.md` §177-178 | Cartelle GraphQL create | 🟢 COMPLETED | Created resolvers/meal |
| P0.4.5 | Create tests structure | `mkdir -p backend/tests/{unit,integration,e2e}/...` | `01_IMPLEMENTATION_GUIDE.md` §180-181 | Cartelle tests create | 🟢 COMPLETED | Created test pyramid structure |

**Milestone P0:** ✅ Workspace pulito, dipendenze aggiornate, struttura creata, client esterni preservati

---

## 📋 Phase 1: Domain Layer - Core (8-10 ore)

**Goal:** Implementare core domain entities, value objects, events, exceptions.

| ID | Task | Description | Reference Doc | Expected Result | Status | Notes |
|----|------|-------------|---------------|-----------------|--------|-------|
| **P1.1** | **Value Objects** | Implementare value objects core | `02_DOMAIN_LAYER.md` §40-150 | 4 value objects implementati e testati | 🟢 COMPLETED | 33 tests passing, commit 9f518a0 |
| P1.1.1 | MealId value object | `domain/meal/core/value_objects/meal_id.py` | `01_IMPLEMENTATION_GUIDE.md` §193-207 | MealId con UUID, frozen dataclass | 🟢 COMPLETED | Includes: generate(), from_string(), __str__() |
| P1.1.2 | Quantity value object | `domain/meal/core/value_objects/quantity.py` | `01_IMPLEMENTATION_GUIDE.md` §209-229 | Quantity con validazione e conversione | 🟢 COMPLETED | Includes: validation, to_grams(), scale() |
| P1.1.3 | Timestamp value object | `domain/meal/core/value_objects/timestamp.py` | `02_DOMAIN_LAYER.md` §100-130 | Timestamp con timezone UTC | 🟢 COMPLETED | Includes: now(), from_iso(), is_today() |
| P1.1.4 | Confidence value object | `domain/meal/core/value_objects/confidence.py` | `02_DOMAIN_LAYER.md` §140-150 | Confidence 0.0-1.0 validato | 🟢 COMPLETED | Includes: high(), medium(), low(), is_reliable() |
| P1.1.5 | Tests value objects | `tests/unit/domain/meal/core/test_value_objects.py` | `01_IMPLEMENTATION_GUIDE.md` §231-233 | Test suite completa value objects | 🟢 COMPLETED | 33 tests, 100% pass rate |
| **P1.2** | **Domain Events** | Implementare eventi di dominio | `02_DOMAIN_LAYER.md` §200-350 | 4 eventi implementati | 🟢 COMPLETED | 20 tests passing, commit 5ab566e |
| P1.2.1 | MealAnalyzed event | `domain/meal/core/events/meal_analyzed.py` | `01_IMPLEMENTATION_GUIDE.md` §239-254 | Evento MealAnalyzed con factory | 🟢 COMPLETED | Includes: source validation, confidence range |
| P1.2.2 | MealConfirmed event | `domain/meal/core/events/meal_confirmed.py` | `02_DOMAIN_LAYER.md` §220-250 | Evento MealConfirmed | 🟢 COMPLETED | Tracks confirmed/rejected entry counts |
| P1.2.3 | MealUpdated event | `domain/meal/core/events/meal_updated.py` | `02_DOMAIN_LAYER.md` §260-280 | Evento MealUpdated | 🟢 COMPLETED | Tracks updated_fields list |
| P1.2.4 | MealDeleted event | `domain/meal/core/events/meal_deleted.py` | `02_DOMAIN_LAYER.md` §290-310 | Evento MealDeleted | 🟢 COMPLETED | Soft delete marker |
| P1.2.5 | Tests domain events | `tests/unit/domain/meal/core/test_events.py` | `02_DOMAIN_LAYER.md` §320-350 | Test suite eventi | 🟢 COMPLETED | 20 tests, validation + immutability |
| **P1.3** | **Core Entities** | Implementare entità core Meal e MealEntry | `02_DOMAIN_LAYER.md` §400-700 | 2 entità implementate | ⚪ NOT_STARTED | - |
| P1.3.1 | MealEntry entity | `domain/meal/core/entities/meal_entry.py` | `01_IMPLEMENTATION_GUIDE.md` §260-295 | MealEntry con nutrienti denormalizzati | ⚪ NOT_STARTED | Include: id, meal_id, name, quantity_g, nutrients |
| P1.3.2 | Meal aggregate | `domain/meal/core/entities/meal.py` | `02_DOMAIN_LAYER.md` §500-650 | Meal aggregate root con metodi business | ⚪ NOT_STARTED | Include: add_entry(), calculate_totals(), confirm() |
| P1.3.3 | Tests entities | `tests/unit/domain/meal/core/test_entities.py` | `02_DOMAIN_LAYER.md` §660-700 | Test suite entità | ⚪ NOT_STARTED | Test business logic |
| **P1.4** | **Domain Exceptions** | Implementare eccezioni custom domain | `02_DOMAIN_LAYER.md` §750-850 | 5+ eccezioni implementate | ⚪ NOT_STARTED | - |
| P1.4.1 | Base exceptions | `domain/meal/core/exceptions/base.py` | `02_DOMAIN_LAYER.md` §760-780 | MealDomainException, ValidationError | ⚪ NOT_STARTED | Base classes per eccezioni |
| P1.4.2 | Specific exceptions | `domain/meal/core/exceptions/*.py` | `02_DOMAIN_LAYER.md` §790-830 | MealNotFound, InvalidQuantity, etc. | ⚪ NOT_STARTED | - |
| P1.4.3 | Tests exceptions | `tests/unit/domain/meal/core/test_exceptions.py` | `02_DOMAIN_LAYER.md` §840-850 | Test suite eccezioni | ⚪ NOT_STARTED | - |
| **P1.5** | **Domain Factories** | Implementare factory per creazione entities | `02_DOMAIN_LAYER.md` §900-1000 | MealFactory implementata | ⚪ NOT_STARTED | - |
| P1.5.1 | MealFactory | `domain/meal/core/factories/meal_factory.py` | `02_DOMAIN_LAYER.md` §920-970 | Factory con metodi create_from_* | ⚪ NOT_STARTED | Include: create_from_photo, create_from_barcode |
| P1.5.2 | Tests factory | `tests/unit/domain/meal/core/test_factories.py` | `02_DOMAIN_LAYER.md` §980-1000 | Test suite factory | ⚪ NOT_STARTED | - |

**Milestone P1:** ✅ Core domain implementato (value objects, events, entities, exceptions, factories) con coverage >90%

---

## 📋 Phase 2: Domain Layer - Capabilities (12-15 ore)

**Goal:** Implementare capabilities Nutrition, Recognition, Barcode con ports.

| ID | Task | Description | Reference Doc | Expected Result | Status | Notes |
|----|------|-------------|---------------|-----------------|--------|-------|
| **P2.1** | **Nutrition Capability** | Implementare capability nutrition con port | `02_DOMAIN_LAYER.md` §1100-1400 | Nutrition capability completa | ⚪ NOT_STARTED | Port per USDA client |
| P2.1.1 | MacroNutrients VO | `nutrition/value_objects/macro_nutrients.py` | `02_DOMAIN_LAYER.md` §1120-1160 | Value object macronutrienti | ⚪ NOT_STARTED | protein, carbs, fat, fiber |
| P2.1.2 | MicroNutrients VO | `nutrition/value_objects/micro_nutrients.py` | `02_DOMAIN_LAYER.md` §1170-1210 | Value object micronutrienti | ⚪ NOT_STARTED | vitamins, minerals |
| P2.1.3 | NutrientProfile entity | `nutrition/entities/nutrient_profile.py` | `02_DOMAIN_LAYER.md` §1220-1280 | Entity profilo nutrizionale completo | ⚪ NOT_STARTED | Include: calculate_per_100g() |
| P2.1.4 | INutritionProvider port | `nutrition/ports/nutrition_provider.py` | `02_DOMAIN_LAYER.md` §1290-1320 | Port (interface) per USDA client | ⚪ NOT_STARTED | Metodo: get_nutrients(label, quantity_g) |
| P2.1.5 | EnrichmentService | `nutrition/services/enrichment_service.py` | `02_DOMAIN_LAYER.md` §1330-1380 | Service orchestrazione enrichment | ⚪ NOT_STARTED | Usa INutritionProvider port |
| P2.1.6 | Tests nutrition | `tests/unit/domain/meal/nutrition/test_*.py` | `02_DOMAIN_LAYER.md` §1390-1400 | Test suite nutrition | ⚪ NOT_STARTED | Mock INutritionProvider |
| **P2.2** | **Recognition Capability** | Implementare capability recognition con port | `02_DOMAIN_LAYER.md` §1500-1800 | Recognition capability completa | ⚪ NOT_STARTED | Port per OpenAI client |
| P2.2.1 | Confidence VO | `recognition/value_objects/confidence.py` | `02_DOMAIN_LAYER.md` §1520-1550 | Value object confidence score | ⚪ NOT_STARTED | Validazione 0.0-1.0 |
| P2.2.2 | FoodLabel VO | `recognition/value_objects/food_label.py` | `02_DOMAIN_LAYER.md` §1560-1590 | Value object label USDA-compatible | ⚪ NOT_STARTED | Validazione formato |
| P2.2.3 | RecognizedFood entity | `recognition/entities/recognized_food.py` | `02_DOMAIN_LAYER.md` §1600-1660 | Entity cibo riconosciuto | ⚪ NOT_STARTED | Include: name, label, quantity, confidence |
| P2.2.4 | IVisionProvider port | `recognition/ports/vision_provider.py` | `02_DOMAIN_LAYER.md` §1670-1700 | Port (interface) per OpenAI client | ⚪ NOT_STARTED | Metodo: recognize_food(photo_url, hint) |
| P2.2.5 | RecognitionService | `recognition/services/recognition_service.py` | `02_DOMAIN_LAYER.md` §1710-1770 | Service orchestrazione recognition | ⚪ NOT_STARTED | Usa IVisionProvider port |
| P2.2.6 | Tests recognition | `tests/unit/domain/meal/recognition/test_*.py` | `02_DOMAIN_LAYER.md` §1780-1800 | Test suite recognition | ⚪ NOT_STARTED | Mock IVisionProvider |
| **P2.3** | **Barcode Capability** | Implementare capability barcode con port | `02_DOMAIN_LAYER.md` §1900-2100 | Barcode capability completa | ⚪ NOT_STARTED | Port per OpenFoodFacts |
| P2.3.1 | BarcodeProduct entity | `barcode/entities/barcode_product.py` | `02_DOMAIN_LAYER.md` §1920-1970 | Entity prodotto da barcode | ⚪ NOT_STARTED | Include: barcode, name, brand, nutrients, image_url |
| P2.3.2 | IBarcodeProvider port | `barcode/ports/barcode_provider.py` | `02_DOMAIN_LAYER.md` §1980-2010 | Port (interface) per OpenFoodFacts | ⚪ NOT_STARTED | Metodo: lookup_barcode(barcode) |
| P2.3.3 | BarcodeService | `barcode/services/barcode_service.py` | `02_DOMAIN_LAYER.md` §2020-2070 | Service orchestrazione barcode | ⚪ NOT_STARTED | Usa IBarcodeProvider port |
| P2.3.4 | Tests barcode | `tests/unit/domain/meal/barcode/test_*.py` | `02_DOMAIN_LAYER.md` §2080-2100 | Test suite barcode | ⚪ NOT_STARTED | Mock IBarcodeProvider |

**Milestone P2:** ✅ Tutte le capabilities implementate con ports definiti. Contratti pronti per Phase 3.

---

## 📋 Phase 3: Infrastructure Layer (15-18 ore)

**Goal:** Adattare client esistenti + implementare nuovi adapters per implementare ports.

| ID | Task | Description | Reference Doc | Expected Result | Status | Notes |
|----|------|-------------|---------------|-----------------|--------|-------|
| **P3.1** | **OpenAI Client Adapter** | Implementare client OpenAI 2.5.0+ con structured outputs | `04_INFRASTRUCTURE_LAYER.md` §49-380 | OpenAI client implementa IVisionProvider | ⚪ NOT_STARTED | Nuovo client con v2.5.0+ |
| P3.1.1 | OpenAIClient class | `infrastructure/ai/openai_client.py` | `04_INFRASTRUCTURE_LAYER.md` §75-220 | Client con structured outputs + caching | ⚪ NOT_STARTED | Implementa IVisionProvider port |
| P3.1.2 | Food recognition prompt | Adattare `ai_models/meal_photo_prompt.py` → `infrastructure/ai/prompts/food_recognition.py` | `01_IMPLEMENTATION_GUIDE.md` §747-755 | Prompts adattati per structured outputs | ⚪ NOT_STARTED | **PRESERVARE** logica esistente |
| P3.1.3 | Circuit breaker setup | Aggiungere `@circuit` decorator | `04_INFRASTRUCTURE_LAYER.md` §160-180 | Circuit breaker configurato (5 failures → 60s) | ⚪ NOT_STARTED | - |
| P3.1.4 | Retry logic | Aggiungere `@retry` decorator | `04_INFRASTRUCTURE_LAYER.md` §190-210 | Retry con exponential backoff | ⚪ NOT_STARTED | - |
| P3.1.5 | Tests OpenAI client | `tests/integration/infrastructure/test_openai_client.py` | `04_INFRASTRUCTURE_LAYER.md` §350-380 | Integration tests con mock/real API | ⚪ NOT_STARTED | Test structured outputs |
| **P3.2** | **USDA Client Adapter** | Adattare client USDA esistente per implementare INutritionProvider | `04_INFRASTRUCTURE_LAYER.md` §387-660 | USDA client adattato | ⚪ NOT_STARTED | **ADATTARE**, non riscrivere |
| P3.2.1 | Spostare USDA client | `ai_models/usda_client.py` → `infrastructure/external_apis/usda/client.py` | `01_IMPLEMENTATION_GUIDE.md` §778-795 | File spostato | ⚪ NOT_STARTED | - |
| P3.2.2 | Implementare INutritionProvider | Aggiungere `class USDAClient(INutritionProvider)` | `01_IMPLEMENTATION_GUIDE.md` §796-820 | Port implementato | ⚪ NOT_STARTED | **PRESERVARE** logica matching esistente |
| P3.2.3 | Add circuit breaker | Aggiungere `@circuit` decorator | `01_IMPLEMENTATION_GUIDE.md` §809-810 | Circuit breaker aggiunto | ⚪ NOT_STARTED | - |
| P3.2.4 | Add retry logic | Aggiungere `@retry` decorator | `01_IMPLEMENTATION_GUIDE.md` §811 | Retry logic aggiunto | ⚪ NOT_STARTED | - |
| P3.2.5 | USDA mapper | `infrastructure/external_apis/usda/mapper.py` (se necessario) | `04_INFRASTRUCTURE_LAYER.md` §550-600 | Mapper USDA response → NutrientProfile | ⚪ NOT_STARTED | Solo se serve mapping aggiuntivo |
| P3.2.6 | USDA categories | `infrastructure/external_apis/usda/categories.py` (se necessario) | `04_INFRASTRUCTURE_LAYER.md` §610-640 | Categorizzazione alimenti | ⚪ NOT_STARTED | Solo se serve |
| P3.2.7 | Tests USDA client | `tests/integration/infrastructure/test_usda_client.py` | `04_INFRASTRUCTURE_LAYER.md` §650-660 | Integration tests USDA | ⚪ NOT_STARTED | Test con mock API |
| **P3.3** | **OpenFoodFacts Adapter** | Adattare client OpenFoodFacts per implementare IBarcodeProvider | `04_INFRASTRUCTURE_LAYER.md` §740-900 | OpenFoodFacts client adattato | ⚪ NOT_STARTED | **ADATTARE**, non riscrivere |
| P3.3.1 | Spostare OpenFoodFacts | `openfoodfacts/adapter.py` → `infrastructure/external_apis/openfoodfacts/client.py` | `01_IMPLEMENTATION_GUIDE.md` §844-860 | File spostato | ⚪ NOT_STARTED | - |
| P3.3.2 | Implementare IBarcodeProvider | Aggiungere `class OpenFoodFactsClient(IBarcodeProvider)` | `01_IMPLEMENTATION_GUIDE.md` §861-877 | Port implementato | ⚪ NOT_STARTED | **PRESERVARE** logica barcode lookup |
| P3.3.3 | Add circuit breaker | Aggiungere `@circuit` decorator | `01_IMPLEMENTATION_GUIDE.md` §867 | Circuit breaker aggiunto | ⚪ NOT_STARTED | - |
| P3.3.4 | OpenFoodFacts mapper | `infrastructure/external_apis/openfoodfacts/mapper.py` (se necessario) | `04_INFRASTRUCTURE_LAYER.md` §850-880 | Mapper OFF response → BarcodeProduct | ⚪ NOT_STARTED | Solo se serve |
| P3.3.5 | Tests OpenFoodFacts | `tests/integration/infrastructure/test_openfoodfacts_client.py` | `04_INFRASTRUCTURE_LAYER.md` §890-900 | Integration tests OFF | ⚪ NOT_STARTED | Test con mock API |
| **P3.4** | **In-Memory Repository** | Implementare repository in-memory per testing | `04_INFRASTRUCTURE_LAYER.md` §1000-1150 | InMemoryMealRepository implementato | ⚪ NOT_STARTED | - |
| P3.4.1 | IMealRepository port | `domain/shared/ports/meal_repository.py` | `04_INFRASTRUCTURE_LAYER.md` §1010-1050 | Port repository definito | ⚪ NOT_STARTED | CRUD + query methods |
| P3.4.2 | InMemoryMealRepository | `infrastructure/persistence/in_memory/meal_repository.py` | `04_INFRASTRUCTURE_LAYER.md` §1060-1130 | Repository in-memory implementato | ⚪ NOT_STARTED | Dict-based storage |
| P3.4.3 | Tests repository | `tests/unit/infrastructure/test_in_memory_repository.py` | `04_INFRASTRUCTURE_LAYER.md` §1140-1150 | Test suite repository | ⚪ NOT_STARTED | - |
| **P3.5** | **Event Bus** | Implementare event bus in-memory | `04_INFRASTRUCTURE_LAYER.md` §1200-1350 | Event bus implementato | ⚪ NOT_STARTED | - |
| P3.5.1 | IEventBus port | `domain/shared/ports/event_bus.py` | `04_INFRASTRUCTURE_LAYER.md` §1210-1240 | Port event bus definito | ⚪ NOT_STARTED | publish(), subscribe() |
| P3.5.2 | InMemoryEventBus | `infrastructure/events/in_memory_bus.py` | `04_INFRASTRUCTURE_LAYER.md` §1250-1320 | Event bus in-memory implementato | ⚪ NOT_STARTED | Dict-based handlers |
| P3.5.3 | Tests event bus | `tests/unit/infrastructure/test_event_bus.py` | `04_INFRASTRUCTURE_LAYER.md` §1330-1350 | Test suite event bus | ⚪ NOT_STARTED | - |
| **P3.6** | **Docker Compose Setup** | Setup Docker Compose per local development | `01_IMPLEMENTATION_GUIDE.md` §891-969 | Docker compose funzionante | ⚪ NOT_STARTED | - |
| P3.6.1 | Create docker-compose.yml | Creare file nella root con MongoDB + Redis + Backend | `01_IMPLEMENTATION_GUIDE.md` §899-932 | File docker-compose.yml creato | ⚪ NOT_STARTED | Include volumes per persistenza |
| P3.6.2 | Update make.sh | Aggiungere target: docker-up, docker-down, docker-logs, docker-restart | `01_IMPLEMENTATION_GUIDE.md` §936-955 | Target Docker aggiunti a make.sh | ⚪ NOT_STARTED | - |
| P3.6.3 | Update Makefile | Aggiungere proxy ai target Docker | `01_IMPLEMENTATION_GUIDE.md` §959-969 | Makefile aggiornato | ⚪ NOT_STARTED | - |
| P3.6.4 | Test Docker setup | `make docker-up` e verificare servizi | README.md §320-330 | Servizi MongoDB + Redis + Backend running | ⚪ NOT_STARTED | - |
| **P3.7** | **Integration Tests** | Test suite completa infrastructure layer | `05_TESTING_STRATEGY.md` §400-550 | Integration tests completi | ⚪ NOT_STARTED | - |
| P3.7.1 | Test OpenAI integration | Test con OpenAI reale (opt-in con env var) | `05_TESTING_STRATEGY.md` §420-460 | Tests OpenAI passano | ⚪ NOT_STARTED | Usare OPENAI_API_KEY |
| P3.7.2 | Test USDA integration | Test con USDA reale (opt-in) | `05_TESTING_STRATEGY.md` §470-500 | Tests USDA passano | ⚪ NOT_STARTED | Usare USDA_API_KEY |
| P3.7.3 | Test OFF integration | Test con OpenFoodFacts reale | `05_TESTING_STRATEGY.md` §510-540 | Tests OFF passano | ⚪ NOT_STARTED | - |

**Milestone P3:** ✅ Infrastructure completa, client adattati implementano ports, Docker setup funzionante

---

## 📋 Phase 4: Application Layer (10-12 ore)

**Goal:** Implementare CQRS commands, queries, orchestrators.

| ID | Task | Description | Reference Doc | Expected Result | Status | Notes |
|----|------|-------------|---------------|-----------------|--------|-------|
| **P4.1** | **Commands** | Implementare tutti i commands CQRS | `03_APPLICATION_LAYER.md` §50-400 | 5 commands implementati | ⚪ NOT_STARTED | - |
| P4.1.1 | AnalyzeMealPhotoCommand | `application/meal/commands/analyze_meal_photo.py` | `03_APPLICATION_LAYER.md` §70-140 | Command + handler photo analysis | ⚪ NOT_STARTED | Include: input DTO, handler, result |
| P4.1.2 | AnalyzeMealBarcodeCommand | `application/meal/commands/analyze_meal_barcode.py` | `03_APPLICATION_LAYER.md` §150-210 | Command + handler barcode analysis | ⚪ NOT_STARTED | - |
| P4.1.3 | AnalyzeMealDescriptionCommand | `application/meal/commands/analyze_meal_description.py` | `03_APPLICATION_LAYER.md` §220-280 | Command + handler text analysis | ⚪ NOT_STARTED | - |
| P4.1.4 | ConfirmMealAnalysisCommand | `application/meal/commands/confirm_meal_analysis.py` | `03_APPLICATION_LAYER.md` §290-340 | Command + handler confirmation | ⚪ NOT_STARTED | 2-step process |
| P4.1.5 | UpdateMealCommand | `application/meal/commands/update_meal.py` | `03_APPLICATION_LAYER.md` §350-370 | Command + handler update | ⚪ NOT_STARTED | - |
| P4.1.6 | DeleteMealCommand | `application/meal/commands/delete_meal.py` | `03_APPLICATION_LAYER.md` §380-400 | Command + handler delete (soft) | ⚪ NOT_STARTED | - |
| P4.1.7 | Tests commands | `tests/unit/application/meal/commands/test_*.py` | `03_APPLICATION_LAYER.md` §410-440 | Test suite commands | ⚪ NOT_STARTED | Mock dependencies |
| **P4.2** | **Queries** | Implementare tutte le queries CQRS | `03_APPLICATION_LAYER.md` §500-850 | 7 queries implementate | ⚪ NOT_STARTED | - |
| P4.2.1 | GetMealQuery | `application/meal/queries/get_meal.py` | `03_APPLICATION_LAYER.md` §520-560 | Query single meal by ID | ⚪ NOT_STARTED | - |
| P4.2.2 | GetMealHistoryQuery | `application/meal/queries/get_meal_history.py` | `03_APPLICATION_LAYER.md` §570-610 | Query meal list con filtri | ⚪ NOT_STARTED | - |
| P4.2.3 | SearchMealsQuery | `application/meal/queries/search_meals.py` | `03_APPLICATION_LAYER.md` §620-660 | Query full-text search | ⚪ NOT_STARTED | - |
| P4.2.4 | GetDailySummaryQuery | `application/meal/queries/get_daily_summary.py` | `03_APPLICATION_LAYER.md` §670-710 | Query aggregato giornaliero | ⚪ NOT_STARTED | - |
| P4.2.5 | RecognizeFoodQuery (atomic) | `application/meal/queries/recognize_food.py` | `03_APPLICATION_LAYER.md` §720-760 | Utility query riconoscimento | ⚪ NOT_STARTED | - |
| P4.2.6 | EnrichNutrientsQuery (atomic) | `application/meal/queries/enrich_nutrients.py` | `03_APPLICATION_LAYER.md` §770-810 | Utility query enrichment | ⚪ NOT_STARTED | - |
| P4.2.7 | SearchFoodByBarcodeQuery (atomic) | `application/meal/queries/search_food_by_barcode.py` | `03_APPLICATION_LAYER.md` §820-850 | Utility query barcode | ⚪ NOT_STARTED | - |
| P4.2.8 | Tests queries | `tests/unit/application/meal/queries/test_*.py` | `03_APPLICATION_LAYER.md` §860-880 | Test suite queries | ⚪ NOT_STARTED | - |
| **P4.3** | **Orchestrators** | Implementare orchestratori per flussi complessi | `03_APPLICATION_LAYER.md` §950-1150 | 3 orchestrators implementati | ⚪ NOT_STARTED | - |
| P4.3.1 | PhotoAnalysisOrchestrator | `application/meal/orchestrators/photo_analysis_orchestrator.py` | `03_APPLICATION_LAYER.md` §970-1030 | Orchestrator photo → recognition → enrichment | ⚪ NOT_STARTED | - |
| P4.3.2 | BarcodeAnalysisOrchestrator | `application/meal/orchestrators/barcode_analysis_orchestrator.py` | `03_APPLICATION_LAYER.md` §1040-1090 | Orchestrator barcode → lookup → enrichment | ⚪ NOT_STARTED | - |
| P4.3.3 | TextAnalysisOrchestrator | `application/meal/orchestrators/text_analysis_orchestrator.py` | `03_APPLICATION_LAYER.md` §1100-1150 | Orchestrator text → parse → enrichment | ⚪ NOT_STARTED | - |
| P4.3.4 | Tests orchestrators | `tests/unit/application/meal/orchestrators/test_*.py` | `03_APPLICATION_LAYER.md` §1160-1180 | Test suite orchestrators | ⚪ NOT_STARTED | Mock services |
| **P4.4** | **Event Handlers** | Implementare event handlers per side effects | `03_APPLICATION_LAYER.md` §1250-1350 | Event handlers implementati | ⚪ NOT_STARTED | - |
| P4.4.1 | MealAnalyzedHandler | `application/meal/event_handlers/meal_analyzed_handler.py` | `03_APPLICATION_LAYER.md` §1270-1300 | Handler per evento MealAnalyzed | ⚪ NOT_STARTED | Log, metrics |
| P4.4.2 | MealConfirmedHandler | `application/meal/event_handlers/meal_confirmed_handler.py` | `03_APPLICATION_LAYER.md` §1310-1330 | Handler per evento MealConfirmed | ⚪ NOT_STARTED | - |
| P4.4.3 | Tests event handlers | `tests/unit/application/meal/event_handlers/test_*.py` | `03_APPLICATION_LAYER.md` §1340-1350 | Test suite handlers | ⚪ NOT_STARTED | - |

**Milestone P4:** ✅ Application layer completo (CQRS + orchestrators + event handlers) con tests

---

## 📋 Phase 5: GraphQL Layer (8-10 ore)

**Goal:** Implementare GraphQL resolvers seguendo strategia atomic queries → aggregate → mutations.

| ID | Task | Description | Reference Doc | Expected Result | Status | Notes |
|----|------|-------------|---------------|-----------------|--------|-------|
| **P5.1** | **Schema Definition** | Definire schema GraphQL completo | `06_GRAPHQL_API.md` §30-550 | schema.graphql completo | ⚪ NOT_STARTED | 6 mutations + 7 queries |
| P5.1.1 | Types definition | Definire types (Meal, MealEntry, etc.) | `06_GRAPHQL_API.md` §140-320 | Types GraphQL definiti | ⚪ NOT_STARTED | Include Union types per errori |
| P5.1.2 | Input types | Definire input types | `06_GRAPHQL_API.md` §330-450 | Input types definiti | ⚪ NOT_STARTED | PhotoAnalysisInput, etc. |
| P5.1.3 | Query/Mutation definition | Definire Query e Mutation types | `06_GRAPHQL_API.md` §55-108 | Query + Mutation definiti | ⚪ NOT_STARTED | - |
| **P5.2** | **Atomic Query Resolvers** | Implementare atomic queries FIRST | `06_GRAPHQL_API.md` §650-850 | 3 atomic queries implementate | ⚪ NOT_STARTED | **START HERE** |
| P5.2.1 | recognizeFood resolver | `graphql/resolvers/meal/recognize_food.py` | `01_IMPLEMENTATION_GUIDE.md` §671-705 | Resolver recognizeFood | ⚪ NOT_STARTED | Testa IVisionProvider isolatamente |
| P5.2.2 | enrichNutrients resolver | `graphql/resolvers/meal/enrich_nutrients.py` | `01_IMPLEMENTATION_GUIDE.md` §677-685 | Resolver enrichNutrients | ⚪ NOT_STARTED | Testa INutritionProvider isolatamente |
| P5.2.3 | searchFoodByBarcode resolver | `graphql/resolvers/meal/search_food_by_barcode.py` | `01_IMPLEMENTATION_GUIDE.md` §687-695 | Resolver searchFoodByBarcode | ⚪ NOT_STARTED | Testa IBarcodeProvider isolatamente |
| P5.2.4 | Tests atomic queries | Test GraphQL per atomic queries | `01_IMPLEMENTATION_GUIDE.md` §697-703 | Tests atomic queries passano | ⚪ NOT_STARTED | Verifica singole capabilities |
| **P5.3** | **Aggregate Query Resolvers** | Implementare aggregate queries SECOND | `06_GRAPHQL_API.md` §900-1100 | 4 aggregate queries implementate | ⚪ NOT_STARTED | Dopo atomic queries |
| P5.3.1 | meal resolver | `graphql/resolvers/meal/meal.py` | `06_GRAPHQL_API.md` §920-970 | Resolver meal(id) | ⚪ NOT_STARTED | - |
| P5.3.2 | mealHistory resolver | `graphql/resolvers/meal/meal_history.py` | `06_GRAPHQL_API.md` §980-1020 | Resolver mealHistory con filtri | ⚪ NOT_STARTED | - |
| P5.3.3 | searchMeals resolver | `graphql/resolvers/meal/search_meals.py` | `06_GRAPHQL_API.md` §1030-1060 | Resolver searchMeals | ⚪ NOT_STARTED | - |
| P5.3.4 | dailySummary resolver | `graphql/resolvers/meal/daily_summary.py` | `06_GRAPHQL_API.md` §1070-1100 | Resolver dailySummary | ⚪ NOT_STARTED | - |
| P5.3.5 | Tests aggregate queries | Test GraphQL per aggregate queries | `06_GRAPHQL_API.md` §1110-1130 | Tests aggregate queries passano | ⚪ NOT_STARTED | - |
| **P5.4** | **Mutation Resolvers** | Implementare mutations LAST | `06_GRAPHQL_API.md` §1200-1600 | 6 mutations implementate | ⚪ NOT_STARTED | Dopo queries |
| P5.4.1 | analyzeMealPhoto mutation | `graphql/resolvers/meal/analyze_meal_photo.py` | `06_GRAPHQL_API.md` §1220-1290 | Mutation analyzeMealPhoto | ⚪ NOT_STARTED | Usa PhotoAnalysisOrchestrator |
| P5.4.2 | analyzeMealBarcode mutation | `graphql/resolvers/meal/analyze_meal_barcode.py` | `06_GRAPHQL_API.md` §1300-1360 | Mutation analyzeMealBarcode | ⚪ NOT_STARTED | Usa BarcodeAnalysisOrchestrator |
| P5.4.3 | analyzeMealDescription mutation | `graphql/resolvers/meal/analyze_meal_description.py` | `06_GRAPHQL_API.md` §1370-1430 | Mutation analyzeMealDescription | ⚪ NOT_STARTED | Usa TextAnalysisOrchestrator |
| P5.4.4 | confirmMealAnalysis mutation | `graphql/resolvers/meal/confirm_meal_analysis.py` | `06_GRAPHQL_API.md` §1440-1490 | Mutation confirmMealAnalysis | ⚪ NOT_STARTED | 2-step process |
| P5.4.5 | updateMeal mutation | `graphql/resolvers/meal/update_meal.py` | `06_GRAPHQL_API.md` §1500-1540 | Mutation updateMeal | ⚪ NOT_STARTED | - |
| P5.4.6 | deleteMeal mutation | `graphql/resolvers/meal/delete_meal.py` | `06_GRAPHQL_API.md` §1550-1590 | Mutation deleteMeal | ⚪ NOT_STARTED | Soft delete |
| P5.4.7 | Tests mutations | Test GraphQL per mutations | `06_GRAPHQL_API.md` §1600-1620 | Tests mutations passano | ⚪ NOT_STARTED | - |

**Milestone P5:** ✅ GraphQL API completo (atomic queries → aggregate → mutations) con tests E2E

---

## 📋 Phase 6: Testing & Quality (6-8 ore)

**Goal:** Completare test coverage e quality checks.

| ID | Task | Description | Reference Doc | Expected Result | Status | Notes |
|----|------|-------------|---------------|-----------------|--------|-------|
| **P6.1** | **E2E Tests** | Implementare test end-to-end completi | `05_TESTING_STRATEGY.md` §600-800 | E2E test suite completa | ⚪ NOT_STARTED | - |
| P6.1.1 | Photo analysis E2E | Test flusso completo photo → meal confermato | `05_TESTING_STRATEGY.md` §620-680 | Test E2E photo passano | ⚪ NOT_STARTED | GraphQL mutation → query |
| P6.1.2 | Barcode analysis E2E | Test flusso completo barcode → meal confermato | `05_TESTING_STRATEGY.md` §690-740 | Test E2E barcode passano | ⚪ NOT_STARTED | - |
| P6.1.3 | Text analysis E2E | Test flusso completo text → meal confermato | `05_TESTING_STRATEGY.md` §750-790 | Test E2E text passano | ⚪ NOT_STARTED | - |
| P6.1.4 | Meal lifecycle E2E | Test CRUD completo meal | `05_TESTING_STRATEGY.md` §800-850 | Test lifecycle passano | ⚪ NOT_STARTED | Create → Read → Update → Delete |
| **P6.2** | **Coverage & Quality** | Verificare coverage e quality metrics | `05_TESTING_STRATEGY.md` §900-1000 | Coverage >90%, quality checks OK | ⚪ NOT_STARTED | - |
| P6.2.1 | Run coverage report | `make test-coverage` | `05_TESTING_STRATEGY.md` §920-940 | Report coverage generato | ⚪ NOT_STARTED | Target: >90% |
| P6.2.2 | Check coverage threshold | Verificare coverage domain/application | `05_TESTING_STRATEGY.md` §950-970 | Domain >95%, Application >90% | ⚪ NOT_STARTED | - |
| P6.2.3 | Run linter | `make lint` | `05_TESTING_STRATEGY.md` §980-990 | Nessun errore linting | ⚪ NOT_STARTED | Ruff |
| P6.2.4 | Run type checker | `make typecheck` | `05_TESTING_STRATEGY.md` §995-1000 | Nessun errore type checking | ⚪ NOT_STARTED | mypy strict |
| **P6.3** | **Documentation** | Generare documentazione API con SpectaQL | `06_GRAPHQL_API.md` §1226-1600 | Docs API generate | ⚪ NOT_STARTED | - |
| P6.3.1 | Setup SpectaQL | Installare SpectaQL e creare config | `06_GRAPHQL_API.md` §1240-1310 | spectaql.yaml configurato | ⚪ NOT_STARTED | - |
| P6.3.2 | Export schema | Script per export schema GraphQL | `06_GRAPHQL_API.md` §1320-1390 | Schema esportato in schema.graphql | ⚪ NOT_STARTED | - |
| P6.3.3 | Generate docs | `make docs` per generare HTML | `06_GRAPHQL_API.md` §1400-1430 | Docs HTML generate in docs/ | ⚪ NOT_STARTED | - |
| P6.3.4 | Setup CI for docs | GitHub Actions per auto-publish | `06_GRAPHQL_API.md` §1500-1600 | CI genera docs su ogni push | ⚪ NOT_STARTED | GitHub Pages |

**Milestone P6:** ✅ Coverage >90%, quality checks OK, docs API generate e pubblicate

---

## 📋 Phase 7: Deployment & Monitoring (4-6 ore)

**Goal:** Deploy in production e setup monitoring.

| ID | Task | Description | Reference Doc | Expected Result | Status | Notes |
|----|------|-------------|---------------|-----------------|--------|-------|
| **P7.1** | **Production Deployment** | Deploy su Render in production | README.md §260-350 | Backend deployed su Render | ⚪ NOT_STARTED | - |
| P7.1.1 | Update Dockerfile | Verificare Dockerfile con nuova struttura | README.md §185-215 | Dockerfile aggiornato | ⚪ NOT_STARTED | COPY nuove cartelle |
| P7.1.2 | Update render.yaml | Verificare config Render | README.md §220-280 | render.yaml verificato | ⚪ NOT_STARTED | buildCommand, startCommand |
| P7.1.3 | Set env vars Render | Configurare OPENAI_API_KEY, USDA_API_KEY, etc. | README.md §240-260 | Env vars configurate | ⚪ NOT_STARTED | Dashboard Render |
| P7.1.4 | Deploy to staging | Deploy su branch staging first | README.md §290-310 | Staging deployment OK | ⚪ NOT_STARTED | Test in staging |
| P7.1.5 | Deploy to production | Merge main e deploy production | README.md §320-340 | Production deployment OK | ⚪ NOT_STARTED | - |
| P7.1.6 | Smoke tests production | Test health endpoint + sample query | README.md §345-350 | Smoke tests passano | ⚪ NOT_STARTED | /health, sample GraphQL query |
| **P7.2** | **Monitoring & Observability** | Setup monitoring e alerting | `04_INFRASTRUCTURE_LAYER.md` §1400-1500 | Monitoring attivo | ⚪ NOT_STARTED | - |
| P7.2.1 | Setup structured logging | Implementare structured logs (JSON) | `04_INFRASTRUCTURE_LAYER.md` §1410-1440 | Logs strutturati | ⚪ NOT_STARTED | Include: request_id, user_id, latency |
| P7.2.2 | Setup metrics | Implementare metrics OpenAI/USDA/OFF calls | `04_INFRASTRUCTURE_LAYER.md` §1450-1480 | Metrics tracked | ⚪ NOT_STARTED | Cache hit rate, latency, errors |
| P7.2.3 | Setup alerting | Configurare alert su Render/Sentry | `04_INFRASTRUCTURE_LAYER.md` §1490-1500 | Alerting configurato | ⚪ NOT_STARTED | Error rate >5%, latency >2s |

**Milestone P7:** ✅ Production deployment completo, monitoring attivo, sistema in produzione

---

## 📈 Progress Tracking

### Status Legend
- ⚪ **NOT_STARTED**: Task non ancora iniziato
- 🔵 **IN_PROGRESS**: Task in corso
- 🟢 **COMPLETED**: Task completato
- 🔴 **BLOCKED**: Task bloccato (dipendenza non risolta)
- 🟡 **ON_HOLD**: Task in pausa

### Completion Criteria
Ogni task è considerato COMPLETED quando:
1. ✅ Codice implementato secondo specification
2. ✅ Tests scritti e passano (coverage target raggiunto)
3. ✅ Code review completato (self-review o peer review)
4. ✅ Documentazione aggiornata (docstrings, comments)
5. ✅ Commit con conventional commit message

---

## 🎯 Critical Path

**Tasks BLOCKING** (da fare per primi):
1. **P0.1** - Upgrade OpenAI 2.5.0+ (CRITICAL)
2. **P0.3** - Selective Cleanup
3. **P0.4** - Create New Structure
4. **P1.x** - Core domain (foundation per tutto)
5. **P2.x** - Ports definition (contratti per infrastructure)
6. **P3.1, P3.2, P3.3** - Client adapters (implementano ports)

**Parallel Work Possible**:
- P4 (Application) può iniziare dopo P2 (ports definiti) e P3.1-3.3 (adapters pronti)
- P5 (GraphQL) può iniziare in parallelo a P4 (usa stessi commands/queries)
- P6 (Testing) incrementale durante tutte le fasi

---

## 📝 Notes & Conventions

### Commit Messages
```
feat(domain): add MealEntry entity
fix(infrastructure): handle USDA API timeout
test(application): add tests for PhotoAnalysisCommand
docs(readme): update quick start guide
refactor(graphql): extract resolver helper
```

### Branch Strategy
- `refactor` - branch principale di sviluppo
- Creare feature branches per task grandi: `refactor/p1-domain-core`
- Merge incrementale in `refactor` dopo ogni milestone

### Test Commands
```bash
make test              # All tests
make test-unit         # Unit tests only
make test-integration  # Integration tests
make test-e2e          # E2E tests
make test-coverage     # Coverage report
```

### Quality Commands
```bash
make lint              # Ruff linter
make typecheck         # mypy type checking
make format            # Black formatter
make quality           # lint + typecheck + format
```

---

## 🚀 Getting Started

1. **Leggi questo documento** completamente per comprendere scope e dependencies
2. **Inizia da P0.1** (Upgrade OpenAI) - BLOCKING per tutto il resto
3. **Procedi sequenzialmente** attraverso le phases
4. **Aggiorna status** di ogni task completato in questo documento
5. **Fai commit frequenti** con conventional commit messages
6. **Verifica milestone** dopo ogni phase prima di procedere

---

**Ultimo aggiornamento:** 22 Ottobre 2025  
**Prossimo task:** P0.1 - Upgrade OpenAI Dependencies
