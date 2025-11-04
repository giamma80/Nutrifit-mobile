# Profilo nutrizionale personalizzato: calcolo e implementazione tecnica

**Version:** 2.0  
**Date:** 31 Ottobre 2025  
**Status:** ✅ MVP Implemented (Phase 9.1-9.4 Complete)

Il profilo nutrizionale personalizzato si basa sui dati dell'utente (peso, altezza, età, sesso, livello di attività) e sull'obiettivo desiderato (definizione "cut", mantenimento "maintain", massa "bulk"). Il processo fondamentale è: (1) stimare il metabolismo basale (BMR) con la formula di Mifflin-St Jeor; (2) moltiplicare il BMR per un fattore di attività (PAL) per ottenere il fabbisogno calorico giornaliero (TDEE); (3) applicare un adeguato deficit o surplus calorico in base all'obiettivo (es. riduzione di ~300–500 kcal/giorno per il "cut"); (4) distribuire le calorie nei macronutrienti (proteine, carboidrati, grassi) secondo raccomandazioni nutrizionali.

**✨ Novità Implementate:**
- ✅ **Dynamic Deficit Tracking**: Tracking del deficit calorico reale (consumato - bruciato) invece di target statico
- ✅ **Macro Consumption Tracking**: Monitoraggio giornaliero di proteine, carboidrati e grassi consumati
- ✅ **Progress Analytics**: Metriche avanzate per aderenza al piano nutrizionale

## Formule di calcolo

* **Metabolismo basale (BMR)**: calcolato con l’equazione di Mifflin-St Jeor. Per gli uomini:
  `BMR = 10 x peso (kg) + 6.25 x altezza (cm) - 5 x età (anni) + 5`
  Per le donne:
  `BMR = 10 x peso (kg) + 6.25 x altezza (cm) - 5 x età (anni) - 161`

* **Fabbisogno calorico giornaliero (TDEE)**: ottenuto moltiplicando il BMR per un indice di attività fisica (PAL). Ad esempio: sedentario *1.2*, attività leggera *1.375*, moderata *1.55*, intensa *1.725*, molto intensa *1.9*. Quindi
  `TDEE = BMR x PAL`

* **Adattamento all’obiettivo**: per il mantenimento si assume generalmente TDEE senza modifiche. Per perdere peso (“cut”) si applica un deficit calorico, tipicamente di 300–500 kcal/giorno (~10–20% del TDEE). Per aumentare massa (“bulk”) si aggiunge un surplus, ad es. +10–20% al TDEE.

* **Distribuzione dei macronutrienti**: una volta stabilite le calorie giornaliere, si dividono in proteine, carboidrati e grassi. Una ripartizione comune è proteine 10–35%, grassi 20–35%, carboidrati 45–65% delle calorie giornaliere.

## Esempio di codice Python modulare

```python
def bmr_mifflin(weight, height, age, sex):
    if sex == 'M':
        return 10 * weight + 6.25 * height - 5 * age + 5
    elif sex == 'F':
        return 10 * weight + 6.25 * height - 5 * age - 161
    else:
        raise ValueError("Sex must be 'M' or 'F'")

def tdee(bmr, activity_level):
    factors = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }
    return bmr * factors.get(activity_level)

def adjust_for_goal(tdee_value, goal):
    if goal == 'cut':
        return tdee_value - 500
    elif goal == 'bulk':
        return tdee_value + 300
    elif goal == 'maintain':
        return tdee_value
    else:
        raise ValueError("Goal must be 'cut', 'maintain', or 'bulk'")

def macronutrient_split(calories, weight, goal):
    if goal == 'cut':
        protein_g = 2.2 * weight
    elif goal == 'bulk':
        protein_g = 2.0 * weight
    else:
        protein_g = 1.8 * weight
    protein_cal = protein_g * 4
    fat_pct = 0.25 if goal != 'bulk' else 0.20
    fat_cal = calories * fat_pct
    fat_g = fat_cal / 9
    carb_cal = calories - (protein_cal + fat_cal)
    carb_g = carb_cal / 4
    return round(protein_g), round(carb_g), round(fat_g)
```

## Estendibilità con Machine Learning

* **Aggiornamento dinamico del TDEE**: col tempo il peso e la composizione corporea cambiano, quindi anche il TDEE va rivalutato. Si possono usare algoritmi di regressione (lineare, random forest, boosting) o **filtri di Kalman** per stime adattive.

* **Dati da utilizzare**: storico del peso, kcal ingerite, dati attività (es. passi, allenamenti, sonno). Questi dati formano una serie temporale personalizzata per ogni utente.

* **Modelli suggeriti**:

  * Regressione lineare
  * Regressione polinomiale
  * ARIMA / Prophet (forecasting)
  * Reti neurali leggere (MLP, LSTM)
  * Kalman Filter per stima TDEE adattiva

* **LLM (Large Language Models)**:

  * generano raccomandazioni nutrizionali in linguaggio naturale
  * rispondono a domande alimentari
  * elaborano piani settimanali in base a profilo, preferenze, allergie
  * possono essere integrati con LangChain / OpenAI / HuggingFace

## Modello Pydantic per GraphQL

```python
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date

class UserData(BaseModel):
    weight: float
    height: float
    age: int
    sex: Literal['M','F']
    activity_level: Literal['sedentary','light','moderate','active','very_active']
    goal: Literal['cut','maintain','bulk']

class NutritionalProfile(BaseModel):
    bmr: float
    tdee: float
    calories_target: float
    protein_g: int
    carbs_g: int
    fat_g: int

class ProgressRecord(BaseModel):
    date: date
    weight: float
    consumed_calories: Optional[float] = None
    
    # ✨ NEW: Dynamic Deficit Tracking
    calories_burned_bmr: Optional[float] = None
    calories_burned_active: Optional[float] = None
    
    # ✨ NEW: Macro Consumption Tracking  
    consumed_protein_g: Optional[float] = None
    consumed_carbs_g: Optional[float] = None
    consumed_fat_g: Optional[float] = None
    
    notes: Optional[str] = None
```

Questo modello è compatibile con framework GraphQL come **Strawberry** e si integra facilmente con query e mutation: calcolo profilo, aggiornamento storico, suggerimenti personalizzati.

---

## ✨ Enhanced Features Implementate (Phase 9.4)

### 1. Dynamic Deficit Tracking System

**Philosophy**: L'obiettivo è mantenere un **deficit/surplus calorico costante**, non un target calorico statico.

**Campi in ProgressRecord:**
- `calories_burned_bmr`: Metabolismo basale giornaliero
- `calories_burned_active`: Calorie da attività fisica
- `calorie_balance` (property): consumed - burned

**Validation:**
```python
def is_deficit_on_track(target_deficit: float, tolerance_kcal: float = 50.0) -> bool:
    """Verifica se il balance reale è vicino al target deficit"""
    # Example: target=-500 (CUT), actual=-480 → True (entro 50 kcal)
```

**Analytics:**
```python
def days_deficit_on_track(start_date, end_date, tolerance=50) -> int:
    """Conta giorni con deficit on track"""

def average_deficit(start_date, end_date) -> float:
    """Media del balance giornaliero"""
```

### 2. Macro Consumption Tracking

**Campi in ProgressRecord:**
- `consumed_protein_g`: Proteine consumate (g)
- `consumed_carbs_g`: Carboidrati consumati (g)  
- `consumed_fat_g`: Grassi consumati (g)

**Methods:**
```python
def update_consumed_macros(protein_g, carbs_g, fat_g):
    """Auto-calcola calories: (P×4 + C×4 + F×9)"""

def are_macros_on_track(target_p, target_c, target_f, tolerance=10.0) -> bool:
    """Verifica se tutti i macro sono entro tolleranza"""

def macro_protein_delta(target) -> float:
    """consumed - target"""
```

**Test Coverage:** 162 tests passing (84 domain + 78 application)


-------


## Estensione Machine Learning: Adattamento Metabolico e Previsione dell'Andamento

### Perché includere il Machine Learning

Il TDEE calcolato inizialmente tramite formule è una stima approssimativa e non statica. Il metabolismo si adatta ai cambiamenti nella massa grassa e magra, all'attività fisica e a fattori ormonali e di stress. Per questo motivo è utile adottare un modello adattivo che aggiorni il TDEE sulla base dell'andamento registrato nel tempo.

### Dati necessari

* Peso corporeo (ideale: misurato più volte a settimana a riposo)
* Consumo calorico giornaliero stimato
* Ripartizione dei macronutrienti
* Attività fisica (es. passi, sessioni allenamento, calorie bruciate)

### Modello di adattamento metabolico (Filtro di Kalman)

Si utilizza un **Filtro di Kalman** per aggiornare dinamicamente la stima del TDEE.

```python
def estimate_tdee_kalman(weight_series, calorie_series):
    # Modello: peso(t) = peso(t-1) + (calorie_in - tdee) / 7700
    from pykalman import KalmanFilter
    import numpy as np

    transition_matrix = np.array([[1, -1/7700], [0, 1]])
    observation_matrix = np.array([[1, 0]])

    kf = KalmanFilter(
        transition_matrices=transition_matrix,
        observation_matrices=observation_matrix,
        initial_state_mean=[weight_series[0], 2500],
        initial_state_covariance=np.eye(2)
    )

    state_means, _ = kf.filter(weight_series)

    estimated_tdee = state_means[:,1]
    return estimated_tdee[-1], estimated_tdee
```

### Modello di previsione del peso (Time Series Forecasting)

È possibile stimare l'andamento futuro del peso usando **Prophet**.

```python
from prophet import Prophet
import pandas as pd

def forecast_weight(weight_series):
    df = pd.DataFrame({
        "ds": pd.date_range(end=pd.Timestamp.today(), periods=len(weight_series)),
        "y": weight_series
    })
    model = Prophet()
    model.fit(df)
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)
    return forecast[['ds','yhat']]
```

### Utilizzo degli LLM per la comunicazione e motivazione

I modelli linguistici possono:

* Fornire feedback motivazionale basato sui dati
* Spiegare variazioni di peso e metabolismo
* Suggerire azioni settimanali personalizzate

Esempio prompt:

```
Analizza questi dati:
Peso medio settimanale, calorie ingerite, TDEE stimato, attività.
Fornisci:
1. Valutazione del progresso
2. Due consigli applicabili questa settimana
3. Un suggerimento alimentare sostenibile
```

### Flow operativo settimanale
1. Valutazione dati biometrici e alimentari (gia presenti attraverso le API del dominio meals e activity)
2. Se non presente creazione del profilo nutrizionale iniziale
3. Aggiornamento TDEE via Kalman
4. Previsione peso futuro via Prophet
5. Generazione feedback via LLM



## API GraphQL: Implementazione del Domain nutritional_profile

### 🎯 Status: MVP In Progress (58.8% Complete)

**Completato (Phase 9.1-9.4):**
- ✅ Dependencies Setup (numpy 2.3.4)
- ✅ Domain Core (value objects, entities, events, exceptions, ports, factory)
- ✅ Calculation Services (BMR, TDEE, Macro)
- ✅ Application Layer (commands, queries, orchestrators)
- ✅ Enhanced Features (dynamic deficit + macro tracking)

**Pending (Phase 9.5-9.7):**
- 🔵 Infrastructure Layer (MongoDB repository + adapters)
- 🔵 GraphQL Layer (types, mutations, queries)
- 🔵 Testing & Quality (E2E tests + documentation)

### GraphQL API Specification

Le seguenti funzionalità GraphQL saranno esposte una volta completato Phase 9.6:

#### Mutations

**1. createNutritionalProfile**
```graphql
mutation CreateNutritionalProfile($input: CreateProfileInput!) {
  createNutritionalProfile(input: $input) {
    profile {
      profileId
      userId
      goal
      bmr
      tdee
      caloriesTarget
      macroSplit {
        proteinG
        carbsG
        fatG
      }
      createdAt
    }
  }
}

input CreateProfileInput {
  userId: String!
  userData: UserDataInput!
  goal: Goal!
  initialWeight: Float!
  initialDate: Date
}

input UserDataInput {
  weight: Float!
  height: Float!
  age: Int!
  sex: Sex!
  activityLevel: ActivityLevel!
}

enum Goal { CUT, MAINTAIN, BULK }
enum Sex { M, F }
enum ActivityLevel { SEDENTARY, LIGHT, MODERATE, ACTIVE, VERY_ACTIVE }
```

**2. updateNutritionalProfile**
```graphql
mutation UpdateNutritionalProfile($input: UpdateProfileInput!) {
  updateNutritionalProfile(input: $input) {
    profile {
      profileId
      # ... same fields as create
      updatedAt
    }
  }
}

input UpdateProfileInput {
  profileId: ID!
  userData: UserDataInput
  goal: Goal
}
```

**3. recordProgress**
```graphql
mutation RecordProgress($input: RecordProgressInput!) {
  recordProgress(input: $input) {
    progressRecord {
      date
      weight
      consumedCalories
      consumedProteinG    # ✨ NEW
      consumedCarbsG      # ✨ NEW
      consumedFatG        # ✨ NEW
      caloriesBurnedBmr   # ✨ NEW
      caloriesBurnedActive # ✨ NEW
      calorieBalance      # ✨ NEW (computed)
      notes
    }
    weightDelta
    daysTracked
  }
}

input RecordProgressInput {
  profileId: ID!
  measurementDate: Date!
  weight: Float!
  consumedCalories: Float
  consumedProteinG: Float    # ✨ NEW
  consumedCarbsG: Float      # ✨ NEW
  consumedFatG: Float        # ✨ NEW
  caloriesBurnedBmr: Float   # ✨ NEW
  caloriesBurnedActive: Float # ✨ NEW
  notes: String
}
```

#### Queries

**1. nutritionalProfile**
```graphql
query GetNutritionalProfile($profileId: ID, $userId: String) {
  nutritionalProfile(profileId: $profileId, userId: $userId) {
    profileId
    userId
    goal
    bmr
    tdee
    caloriesTarget
    macroSplit {
      proteinG
      carbsG
      fatG
    }
    progressHistory {
      date
      weight
      consumedCalories
      consumedProteinG    # ✨ NEW
      consumedCarbsG      # ✨ NEW
      consumedFatG        # ✨ NEW
      caloriesBurnedTotal # ✨ NEW
      calorieBalance      # ✨ NEW
    }
    createdAt
    updatedAt
  }
}
```

**2. progressScore**
```graphql
query CalculateProgressScore($input: ProgressScoreInput!) {
  progressScore(input: $input) {
    weightDelta
    targetWeightDelta
    averageDailyCalories
    daysOnTrack          # Legacy (TDEE validation)
    daysDeficitOnTrack   # ✨ NEW (deficit validation)
    averageDeficit       # ✨ NEW
    totalMeasurements
    adherenceRate
  }
}

input ProgressScoreInput {
  profileId: ID!
  startDate: Date!
  endDate: Date!
}
```

**3. forecastWeight** (Phase 9 Step 2 - ML Enhancement, DEFERRED)
```graphql
query ForecastWeight($profileId: ID!, $days: Int!) {
  forecastWeight(profileId: $profileId, days: $days) {
    forecastDates
    forecastWeights
    confidenceIntervalLower
    confidenceIntervalUpper
    estimatedTdee  # Kalman filter estimate
  }
}
```

### Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Domain Core | ✅ COMPLETED | 84 tests, ~90% coverage |
| Calculation Services | ✅ COMPLETED | 30 tests, 100% coverage |
| Application Layer | ✅ COMPLETED | 78 tests, ~85% coverage |
| Dynamic Deficit Tracking | ✅ COMPLETED | 20 tests |
| Macro Consumption Tracking | ✅ COMPLETED | 13 tests |
| Infrastructure Layer | 🔵 PENDING | MongoDB repository + adapters |
| GraphQL Types | 🔵 PENDING | Strawberry types |
| GraphQL Mutations | 🔵 PENDING | 3 mutations |
| GraphQL Queries | 🔵 PENDING | 2 queries (3rd deferred) |
| E2E Tests | 🔵 PENDING | test_nutritional_profile.sh |
| ML Enhancement (Kalman/Prophet) | ⏸️ DEFERRED | Phase 9 Step 2 |
| LLM Feedback | ⏸️ DEFERRED | Phase 9 Step 3 |

**Total Progress:** 58.8% (10/17 MVP tasks)  
**Estimated Remaining Time:** 18-24h (Infrastructure + GraphQL + Testing)
