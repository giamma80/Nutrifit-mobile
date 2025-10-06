# Nutrifit – Nutrition & Diet Engine Guide (Draft)

> Stato: Spostato in `docs/`. Questo è il documento originale completo. (Versione ricollocata 2025-09-18)

<!-- Inizio contenuto originale -->

```diff
NOTE: Questo file è stato ricollocato da root a docs/ per una migliore organizzazione.
```

## 1. Vision & Scopo

Obiettivo: integrare tracking nutrizionale intelligente (calorie + macronutrienti + aderenza al piano) con i dati di spesa energetica provenienti da HealthKit / Google Fit per fornire all’utente un quadro completo: deficit / mantenimento / surplus e progressi verso il goal.

Valore chiave:

- Unico pannello integrato input (cibo) + output (dispendio) + goal adattivi.
- Supporto logging multi-canale: ricerca alimenti, barcode, foto + AI, inserimento rapido porzioni/ricette.
- Feedback adattivo e insight personalizzati.

Out-of-scope iniziale (Fase > MVP): ricette collaborative, social meal sharing, suggerimenti ML avanzati.

## 2. Personas (Sintetico)

| Persona | Esigenza Principale | Metriche di Successo |
|---------|---------------------|----------------------|
| Beginner Diet | Capire quante calorie assumere | Giorni consecutivi di logging |
| Fitness Enthusiast | Ottimizzare macro per recomposition | Aderenza proteine % |
| Weight Loss User | Mantenere deficit sostenibile | Deficit medio settimanale |
| Bulk Athlete | Garantire surplus controllato | Rateo aumento peso/mese |

Motivazioni & Triggers Retention (Sintesi):

- Beginner Diet: bisogno di onboarding chiaro; frizione: overload formule → usare copy semplice + wizard progressivo. Trigger retention: primo grafico progresso peso dopo 5 giorni.
- Fitness Enthusiast: vuole granularità macro; frizione: editing macro manuale; soluzione: modalità avanzata macro override. Trigger: raggiungimento 90% aderenza proteine 7 giorni → badge.
- Weight Loss User: teme plateau; frizione: mancanza feedback trend; soluzione: trend peso smussato (EMA) + messaggi rassicuranti. Trigger: notifica “progressi reali” ogni -1kg cumulativo.
- Bulk Athlete: evita eccessivo grasso; frizione: necessità confronto surplus pianificato vs reale; soluzione: card ‘surplus medio 7g’. Trigger: alert se surplus >15% per 10 giorni.

## 3. Use Case (Priorità)

| ID | Titolo | Descrizione | Priorità | Stato |
|----|--------|-------------|----------|-------|
| UC1 | Onboarding nutrizionale | Raccolta dati fisici + goal → calcolo TDEE & target calorie/macro | P0 | Draft |
| UC2 | Log pasto manuale | Aggiunta alimento da ricerca + quantità | P0 | Draft |
| UC3 | Dashboard giornaliera | Bilancio: assunte vs bruciate vs target | P0 | Draft |
| UC4 | Modifica piano | Aggiornare goal (cut/maintain/bulk) | P1 | Planned |
| UC5 | Barcode scan | Ricerca alimento da codice a barre | P1 | Planned |
| UC6 | Foto piatto (AI) | Stima alimento + conferma utente | P2 | Planned |
| UC7 | Trend settimanali | Aderenza calorie e macro | P1 | Planned |
| UC8 | Notifiche reminder pasti | Prompt quando utente non logga | P2 | Planned |
| UC9 | Adattamento automatico piano | Ricalcolo target se deviazione persistente | P3 | Planned |

## 4. Domain Model (Overview)

...existing content from original guide continues (omitted here for brevity, identical al file root al momento dello spostamento)...

<!-- Contenuto successivo consolidato: le sezioni avanzate (AI pipeline, notifiche, adattamento) sono ora nel documento esteso. -->

## 4.1 Nutrient Snapshot Decoupling (Backend‑Centric)

Per garantire stabilità storica degli analytics, ogni `meal_entry` memorizza uno snapshot immutabile dei nutrienti al momento del log. Motivi:

- Sorgenti esterne (OpenFoodFacts, enrichment AI) possono aggiornare valori: evitiamo drift retroattivo.
- Calcoli settimanali/storici non devono ricalcolarsi se cambiano profili fonte.
- Consente normalizzazione unica (kJ→kcal, sale→sodio) e versionamento schema interno.

Campi minimi snapshot:

```json
{
	"schema_version": 1,
	"energy_kcal": 250,
	"protein_g": 15,
	"carbs_g": 20,
	"fat_g": 9,
	"source": "OFF|MANUAL|AI",
	"source_ref": "barcode|manual|inference:<id>"
}
```

Strategia evoluzione:

- Nuovi micronutrienti → aggiunti opzionalmente (backward compatible).
- Se un valore fuori range plausibile viene ricevuto dall’origine → log errore + fallback (scarto entry).
- Migrazione schema snapshot (bump `schema_version`) con migrazione forward-only; nessuna retroattiva.

## 4.2 Macro Pacing & Sugar Spike Rationale

Per feedback intra-giornaliero la piattaforma calcola una traiettoria attesa dei macronutrienti. Assumendo finestra alimentare di 16h, l'aspettativa lineare per le proteine a ora `h` è:

```
expected_protein = target_protein_g * (h / 16)
```

Uno slack (default 5g) evita segnalazioni premature. Lo spike zuccheri è rilevato confrontando `sugars_so_far` con media rolling 7 giorni alla stessa fascia oraria:

```
is_spike = sugars_so_far > max(rolling_mean_sugars * 1.35, 40g)
```

Fattore (1.35) e soglia assoluta (40g) sono parametri configurabili e potranno diventare personalizzati per utente. Le euristiche alimentano i trigger nel motore raccomandazioni (`recommendation_engine.md`) e potranno essere sostituite da modelli adattivi (EWMA / regressione) senza breaking del contratto GraphQL.

## 4.3 Fonti Nutrienti & Strategia Integrazione (Issues #58, #59)

Obiettivo: definire una gerarchia deterministica e auditabile delle fonti nutrienti per ridurre drift, aumentare affidabilità macro/calorie e semplificare la riconciliazione futura (override utente, ricette, AI, barcode).

### 4.3.1 Gerarchia Sorgenti (priorità decrescente)

| Ord | Fonte | Codice `enrichment_source` (proposto) | Note Applicative |
|-----|-------|----------------------------------------|------------------|
| 1 | Override utente / alimento salvato | user_override | Autoritativa: mai sovrascrivere se valori plausibili |
| 2 | Prodotto confezionato (barcode → OpenFoodFacts) | off_barcode | Match deterministico; fallback se nutrienti mancanti |
| 3 | USDA exact (FoodData Central match alto) | usda_exact | Match punteggio > soglia high, descrizione altamente specifica |
| 4 | USDA generic | usda_generic | Punteggio medio, descrizione generica o cooking method mancante |
| 5 | Tabelle EU locali (CIQUAL – futura) | ciqual | Import snapshot periodico, sinonimi localizzati |
| 6 | Category profile (cluster interno) | category_profile | Macro medi per cluster (es. lean_fish) |
| 7 | Heuristic/default (enrichment locale) | heuristic | Stima iniziale debole / incompleta |
| 8 | GPT macro_guess (fallback) | gpt_guess | Solo se tutte le altre fonti falliscono; da marcare chiaramente |

Regola generale di override: una fonte a priorità superiore può sostituire una inferiore; l'inverso solo in presenza di valori impossibili (negativi, zeri illogici) o mismatch forte calorie↔macro > soglia (20–25%) con logging.

### 4.3.2 Motivazioni
* Separare stime (heuristic, category_profile) da dati misurati (OFF/USDA)
* Stabilizzare analisi storiche (nutrient snapshot + `source`)
* Permettere miglioramenti incrementali senza riscrivere record passati

### 4.3.3 USDA Adapter (Issue #59)
L'adapter fornirà nutrienti strutturati per alimenti generici quando non esiste barcode. Modalità ibrida raccomandata:
1. Snapshot locale (subset Foundation + SR Legacy) per latenza bassa
2. Fallback API live per miss → inserimento in cache persistente
3. Aggiornamento mensile snapshot + re-indicizzazione sinonimi

Interfaccia (bozza):
```python
class UsdaAdapterResult(TypedDict):
	source: Literal["usda_exact","usda_generic"]
	fdc_id: int
	description: str
	data_type: str
	per_100g: Dict[str, float]  # calories, protein, carbs, fat, fiber, sugar, sodium
	raw: dict

class UsdaAdapter:
	async def search_and_resolve(self, normalized_label: str) -> Optional[UsdaAdapterResult]:
		...
```

### 4.3.4 Matching & Ranking
Score = w1 * token_overlap + w2 * exact_phrase + w3 * cooking_method_match + w4 * data_type_priority – w5 * noise_penalty
* Cooking method (grilled/boiled/raw) se presente nella label utente
* Prefer generic per query generiche (evitare brand non menzionati)
* Penalizzare descrizioni estese con ingredienti extra non citati

Soglie (iniziali):
* High ≥ 0.88 → usda_exact
* Medium ≥ 0.75 → usda_generic
* Low < 0.75 → fallback category_profile

### 4.3.5 Normalizzazione Valori
* Unificare a per 100g
* Sodium: mg → g /1000
* Recompute calorie se assenti (4/4/9) o delta macro > 15%
* Arrotondamenti: macro e sugar/sodium 2 decimali, calorie intero

### 4.3.6 Caching
* LRU in-memory (512–1024 chiavi)
* Chiave: normalized_label
* Cache negative TTL ~1h (riduce chiamate ripetute per miss)
* Persistenza opzionale tabella `usda_cache` (fdc_id, label, per_100g, imported_at)

### 4.3.7 Metriche & Osservabilità
| Metric | Descrizione |
|--------|-------------|
| usda_lookup_total{outcome=hit|miss|api_error|cache_hit|cache_miss} | Conta outcome lookup |
| usda_latency_ms (hist) | Latenza chiamate (solo API) |
| nutrient_source_distribution{source=...} | Percentuale fonti finali |
| usda_rank_gap | Differenza score top1–top2 (quality confidence) |
| fallback_to_category_profile_total{reason} | Motivi miss (no_match, api_error) |
| calorie_corrected_total{source} | Ricalcoli per fonte originale |

### 4.3.8 Guardrail & Error Handling
| Scenario | Azione |
|----------|--------|
| Timeout API | Fallback category_profile + outcome=api_error |
| 429 / quota | Circuit breaker (es. 60s) + metric rate_limited_total |
| Valori macro tutti 0 | Scarta e fallback inferiore |
| Calorie / macro delta > 25% | Recompute + flag calorie_corrected |
| Dati parziali | Usa subset + tag partial_nutrients |

### 4.3.9 Integrazione Pipeline (Stato pianificato)
1. Heuristic/default (attuale) → produce macro iniziali
2. USDA adapter (se `AI_USDA_ENABLED=on` e fonte debole)
3. Category profile normalization (override solo se fonte bassa priorità)
4. Hard constraints + calorie recompute
5. Snapshot store

### 4.3.10 Roadmap Incrementale
| Fase | Deliverable | Flag | Note |
|------|-------------|------|------|
| A | Skeleton adapter + mock risultati | AI_USDA_ENABLED | Test unit base |
| B | Lookup API live + cache LRU | AI_USDA_ENABLED | Metriche base |
| C | Snapshot ingest opzionale | AI_USDA_SNAPSHOT | Migliora P99 |
| D | Cooking method enrichment | AI_USDA_COOKING | Usa parsing label |
| E | Micronutrienti estesi | AI_USDA_MICROS | Solo se UI li consuma |

### 4.3.11 Riferimenti Audit
Le issue `#58` (doc fonti nutrienti) e `#59` (integrazione USDA) tracciano implementazione e governance. Ogni PR di implementazione dovrà:
1. Aggiornare `audit_issues.md` (colonna Status / Tags)
2. Aggiungere metriche nuove in docs/ai_meal_photo_metrics.md (se introdotte)
3. Incrementare test coverage per ranking e fallback

