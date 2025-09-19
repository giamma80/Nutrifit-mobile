# Rule Engine DSL (Draft)

Obiettivo: definire regole di notifica / adattamento piano nutrizionale in formato dichiarativo YAML.

## Concetti Chiave

- `trigger`: evento o scheduler che avvia la valutazione.
- `conditions`: insieme di condizioni tutte vere (AND implicito) per attivare l'azione.
- `actions`: una o più azioni da eseguire (es. invio notifica, adattamento target).
- `throttle`: finestra di soppressione per evitare spam.
- `priority`: ordinamento quando più regole emettono contemporaneamente.
- `enabled`: feature flag rapida.

## Esempio Base (Notifica Pasti Mancanti)

```yaml
id: meal_reminder_breakfast
version: 1
description: Promemoria colazione se non loggato entro le 09:30 locali
enabled: true
trigger:
  type: schedule
  cron: "30 9 * * *"   # 09:30 ogni giorno
conditions:
  - type: no_meal_logged_in_window
    meal_type: BREAKFAST
    window_hours: 3
  - type: user_goal_active
    goal: WEIGHT_LOSS
throttle:
  window_hours: 4
actions:
  - type: push_notification
    template_id: breakfast_reminder_v1
    variables:
      hint: "Proteine per iniziare la giornata"
priority: 50
metadata:
  category: reminder
  owner: nutrition
```

## Esempio Adattamento Piano

```yaml
id: adaptive_calorie_adjustment_weekly
version: 1
description: Adatta target calorie se deviazione media 7g > 10%
enabled: true
trigger:
  type: event
  name: weekly_summary_computed
conditions:
  - type: deviation_over_threshold
    metric: CALORIES
    window_days: 7
    threshold_pct: 0.10
    direction: ABOVE # or BELOW
  - type: adherence_samples_min
    window_days: 7
    min_days: 5
actions:
  - type: adjust_plan_targets
    max_step_pct: 0.15
    clamp_min_kcal: 1400
    clamp_max_kcal: 3500
priority: 90
metadata:
  category: adaptation
```

## Schema Logico

```yaml
id: string (snake_case unico)
version: integer >=1
description: string opzionale
enabled: boolean (default true)
trigger:
  type: schedule|event
  # schedule
  cron: string (se type=schedule)
  # event
  name: string (se type=event)
conditions:   # lista (può essere vuota --> sempre vero)
  - type: <condition_type>
    ...parametri specifici...
throttle:
  window_hours: int >=1 (opzionale)
actions:      # lista >=1
  - type: <action_type>
    ...parametri specifici...
priority: int (default 100)
metadata: map<string, scalar>
```

### Condition Types (MVP)

| type | Parametri | Descrizione |
|------|-----------|-------------|
| no_meal_logged_in_window | meal_type, window_hours | Nessun pasto di quel tipo nelle ultime X ore |
| user_goal_active | goal | Goal nutrizionale corrente corrisponde |
| deviation_over_threshold | metric, window_days, threshold_pct, direction | Deviazione aggregata sopra/sotto soglia |
| adherence_samples_min | window_days, min_days | Numero giorni con dati validi >= min |

### Action Types (MVP)

| type | Parametri | Effetto |
|------|-----------|---------|
| push_notification | template_id, variables(map) | Invia push con template e variabili |
| adjust_plan_targets | max_step_pct, clamp_min_kcal, clamp_max_kcal | Modifica target calorico/macro |

## Validazioni Principali

1. `id` unico nel set caricato.
2. `actions` non vuoto.
3. Se trigger.type = schedule → campo `cron` richiesto.
4. Se trigger.type = event → campo `name` richiesto.
5. Ogni condition type riconosciuto; parametri obbligatori presenti.
6. Nessun duplicato di stessa condition exact (per semplificare evaluation).
7. `priority` intero (range consigliato 1–100, più alto = più importante).
8. Se presente `throttle.window_hours` deve essere >=1.

## Estensioni Future (Ideas)

- Operatore OR / gruppi condizionali (per ora solo AND implicito).
- Azione `schedule_followup` per creare reminder secondario.
- Condition `streak_days` (giorni consecutivi logging minimo X).
- Embedded mini-expression DSL per condizioni numeriche generiche.

## File Multipli

Le regole possono essere salvate singolarmente (`rules/*.yml`) oppure in un file aggregato (`rules.yaml` con elenco). Il parser accetterà entrambi.

## Esempio File Multi-Regola

```yaml
rules:
  - id: meal_reminder_lunch
    version: 1
    trigger: { type: schedule, cron: "00 13 * * *" }
    actions:
      - type: push_notification
        template_id: lunch_reminder_v1
    conditions:
      - type: no_meal_logged_in_window
        meal_type: LUNCH
        window_hours: 4
  - id: adaptive_calorie_adjustment_weekly
    version: 1
    trigger: { type: event, name: weekly_summary_computed }
    conditions:
      - type: deviation_over_threshold
        metric: CALORIES
        window_days: 7
        threshold_pct: 0.10
        direction: ABOVE
    actions:
      - type: adjust_plan_targets
        max_step_pct: 0.15
        clamp_min_kcal: 1400
        clamp_max_kcal: 3500
```

---

_Draft v0.1 – soggetto a cambi._
