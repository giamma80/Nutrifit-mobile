# Profilo nutrizionale personalizzato: calcolo e implementazione tecnica

Il profilo nutrizionale personalizzato si basa sui dati dell’utente (peso, altezza, età, sesso, livello di attività) e sull’obiettivo desiderato (definizione “cut”, mantenimento “maintain”, massa “bulk”). Il processo fondamentale è: (1) stimare il metabolismo basale (BMR) con la formula di Mifflin-St Jeor; (2) moltiplicare il BMR per un fattore di attività (PAL) per ottenere il fabbisogno calorico giornaliero (TDEE); (3) applicare un adeguato deficit o surplus calorico in base all’obiettivo (es. riduzione di ~300–500 kcal/giorno per il “cut”); (4) distribuire le calorie nei macronutrienti (proteine, carboidrati, grassi) secondo raccomandazioni nutrizionali.

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
    tdee: float
    consumed_calories: Optional[float] = None
```

Questo modello è compatibile con framework GraphQL come **Strawberry** e si integra facilmente con query e mutation: calcolo profilo, aggiornamento storico, suggerimenti personalizzati.


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



## api graphql: implementazione del domain nutritional_profile

è necessario implementare a questo punto un nuovo domain nutritional_profile che esponga le seguenti funzionalità GraphQL:

*  una mutation che prende in ingresso le informazioni utente e crea il profilo nutrizionale
* una mutation che fa l'eventuale update in caso di richiesta di modifica 
* una query che recupera le informazioni
* una query che effettua un forecast per raggiungere l'obiettivo
* una query che riceve in ingresso i dati biometrici aggiornati e la data, e risponde con uno score rispetto al punto di partenza e allo stato di avanzamento
