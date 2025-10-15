# Nutrifit Documentation Index - Aggiornato

**Ultimo aggiornamento:** 15 ottobre 2025  
**Versione sistema:** 0.4.x (con dishHint support)

## 📚 Struttura Documentazione

### Core System
- **[README.md](../README.md)** - Overview progetto e quick start
- **[CHANGELOG.md](../CHANGELOG.md)** - Cronologia modifiche e release
- **[audit_issues.md](../audit_issues.md)** - Tracciamento issue e resolution status

### Backend Architecture  
- **[backend_architecture_plan.md](backend_architecture_plan.md)** - Roadmap architetturale B0-B9
- **[current-status.md](../backend/docs/current-status.md)** - Stato corrente consolidato
- **[data_ingestion_contract.md](data_ingestion_contract.md)** - Contratto ingestion dati

### GraphQL & Schema
- **[graphql_schema_draft.md](graphql_schema_draft.md)** - Schema evolutivo completo  
- **[schema_contract_policy.md](schema_contract_policy.md)** - Policy evoluzione schema
- **[schema_diff.md](schema_diff.md)** - Diff semantico e classificazione

### AI Meal Photo System 🆕
- **[ai_meal_photo.md](ai_meal_photo.md)** - **Main doc** - Two-step flow + dishHint support
- **[ai_food_recognition_prompt.md](ai_food_recognition_prompt.md)** - Prompt GPT-4V + dishHint integration
- **[ai_meal_photo_errors.md](ai_meal_photo_errors.md)** - Error taxonomy e handling
- **[ai_food_pipeline_README.md](ai_food_pipeline_README.md)** - Pipeline AI overview
- **[ai_meal_photo_metrics.md](../backend/docs/ai_meal_photo_metrics.md)** - Adapter pattern + metriche

### Health & Activity
- **[health_totals_sync.md](health_totals_sync.md)** - Health totals delta system
- **[recommendation_engine.md](recommendation_engine.md)** - Recommendation engine design

### Domain Guides
- **[nutrifit_nutrition_guide.md](nutrifit_nutrition_guide.md)** - Guida dominio nutrizionale
- **[mobile_architecture_plan.md](mobile_architecture_plan.md)** - Roadmap mobile M0-M9

### Advanced/Future
- **[rule_engine_DSL.md](rule_engine_DSL.md)** - Rule engine DSL specification

## 🎯 Feature Status Summary

### ✅ Production Ready
- **Core GraphQL API**: Product lookup, CRUD pasti, daily summary
- **AI Meal Photo**: GPT-4V analysis con **supporto dishHint** 
- **Health Activity**: Delta-based totals sync
- **Nutrient System**: Immutable snapshots + enrichment
- **Quality Gates**: CI/CD + preflight validation

### 🔄 In Development  
- **Mobile/Web Scaffold**: Flutter + React con GraphQL codegen
- **Advanced AI Pipeline**: USDA integration, category profiles
- **Observability**: Prometheus metrics production-ready

### 📋 Planned
- **Activity Timeline**: Granular queries da minute events
- **Recommendations Engine**: Trigger-based recommendations
- **Performance**: Advanced caching + query optimization

## 📈 Recent Major Updates

### dishHint Feature (15 ottobre 2025)
- ✅ Campo opzionale `dishHint: String` in `AnalyzeMealPhotoInput`
- ✅ Prompt enhancement: `"Suggerimento: potrebbe essere {dish_hint}"`
- ✅ Full-stack implementation attraverso tutti i layer
- ✅ V2 domain-driven service path attivato
- ✅ Comprehensive logging per debugging
- ✅ Test coverage completa

### System Health
- ✅ `make preflight` passing (linting, tests, schema)
- ✅ CI/CD pipeline attiva e stabile
- ✅ Documentation aggiornata e sincronizzata
- ✅ Quality metrics tracking

## 🔗 Cross-References

### AI Meal Photo Complete Flow
1. [ai_meal_photo.md](ai_meal_photo.md) → Main documentation
2. [ai_food_recognition_prompt.md](ai_food_recognition_prompt.md) → Prompt specifics + dishHint
3. [ai_meal_photo_errors.md](ai_meal_photo_errors.md) → Error handling
4. [ai_meal_photo_metrics.md](../backend/docs/ai_meal_photo_metrics.md) → Observability

### Architecture Evolution
1. [backend_architecture_plan.md](backend_architecture_plan.md) → Strategic roadmap
2. [current-status.md](../backend/docs/current-status.md) → Current state
3. [graphql_schema_draft.md](graphql_schema_draft.md) → Future schema evolution

### Data & Contracts
1. [data_ingestion_contract.md](data_ingestion_contract.md) → Data contracts
2. [health_totals_sync.md](health_totals_sync.md) → Activity sync patterns
3. [schema_contract_policy.md](schema_contract_policy.md) → Schema governance

## 🚀 Next Actions

1. **Priorità Alta**: Mobile/Web scaffold con dishHint support
2. **Priorità Media**: Advanced AI enrichment pipeline  
3. **Priorità Bassa**: Performance optimization + advanced metrics

---

*Questo indice viene aggiornato ad ogni major feature release.*