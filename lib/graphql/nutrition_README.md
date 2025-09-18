# Nutrition GraphQL Module

Questo modulo definisce lo schema e le operazioni GraphQL relative al dominio nutrizione (alimenti, pasti, piano nutrizionale, AI inference).

## Struttura
```
lib/graphql/
  schema_nutrition.graphql
  fragments/
    nutrition_fragments.graphql
  queries/nutrition/
    nutrition_queries.graphql
  nutrition_README.md
```

## Integrazione Codegen
Aggiorna `build.yaml` aggiungendo il globo delle query nutrizione se non già presente:
```yaml
builders:
  graphql_codegen:
    options:
      schema: "lib/graphql/schema.graphql"   # schema principale (puoi concatenare schema_nutrition.graphql in build step) 
      queries_glob: "lib/graphql/queries/**/*.graphql"
      output: "lib/graphql/generated/"
      scalar_mapping:
        - graphql_type: DateTime
          dart_type: DateTime
        - graphql_type: Date
          dart_type: DateTime
```

Se usi schema modulare:
1. Script build unisce `schema.graphql` + `schema_nutrition.graphql` → `combined_schema.graphql`.
2. Imposta `schema: lib/graphql/combined_schema.graphql` nel build.

## Naming Convenzioni
- Fragments: `*Parts` suffix (es. `MealEntryParts`).
- Queries: verbo o contesto (`GetDailyNutrition`).
- Paginazione: usare sempre `Connection` pattern per dataset potenzialmente grandi.

## Estensioni Future
- Subscription per aggiornamenti in tempo reale (es. `mealLogged` stream).
- Filtri avanzati (range macro, fuzzy search server-side).
- Federation (es. Apollo) con chiavi su `FoodItem(id)`.

## Testing Consigliato
- Contract test: snapshot file schema combinato.
- Query di ricerca: test paginazione (prima pagina, pagina successiva, fine lista).
- Mutations: validazione mapping nutriente calcolato.

## TODO
- Aggiungere directive @auth per restrizioni per utente.
- Uniformare error handling (union tipo `NutritionError`).
- Documentare possibili codici errore standardizzati.
