# 🥗 Nutritional Profile Domain - Architecture Documentation

**Version:** 1.0  
**Date:** 30 Ottobre 2025  
**Status:** 📝 Design Phase  
**Implementation:** Phase 9 (MVP Iterative Approach)

---

## 🎯 Overview

Il dominio **Nutritional Profile** gestisce la creazione, aggiornamento e tracking del profilo nutrizionale personalizzato per ogni utente. Include:

- **Calcolo metabolismo basale (BMR)** - Formula Mifflin-St Jeor
- **Calcolo fabbisogno calorico (TDEE)** - BMR × Physical Activity Level (PAL)
- **Distribuzione macronutrienti** - Proteine, carboidrati, grassi per obiettivo
- **Tracking progresso** - Peso, calorie consumate, avanzamento obiettivi
- **ML Forecasting** (Step 2) - Predizione peso futuro, TDEE adattivo
- **LLM Feedback** (Step 3) - Motivazione e suggerimenti personalizzati

---

## 🏗️ Architecture Principles

### Clean Architecture & DDD

```
┌─────────────────────────────────────────────────────────┐
│              GraphQL Layer (Interface)                  │
│  nutritionalProfile, createProfile, recordProgress      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│           Application Layer (Use Cases)                 │
│  Commands: CreateProfile, UpdateProfile, RecordProgress │
│  Queries: GetProfile, CalculateProgress                 │
│  Orchestrator: ProfileOrchestrator                      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Domain Layer (Business Logic)              │
│  Core: NutritionalProfile, ProgressRecord               │
│  Calculation: BMRService, TDEEService, MacroService     │
│  ML: KalmanTDEEService, WeightForecastService (Step 2)  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│         Infrastructure Layer (Adapters)                 │
│  Persistence: MongoProfileRepository                    │
│  Calculation: BMRCalculatorAdapter, etc.                │
│  ML: KalmanCalculator, ProphetForecaster (Step 2)       │
└─────────────────────────────────────────────────────────┘
```

### Key Patterns

- **Aggregate Root**: `NutritionalProfile` (consistency boundary)
- **Value Objects**: Immutable, self-validating (UserData, MacroSplit)
- **Domain Events**: ProfileCreated, ProfileUpdated, ProgressRecorded
- **Ports & Adapters**: Domain defines interfaces, Infrastructure implements
- **CQRS**: Separate commands (write) and queries (read)
- **Factory Pattern**: NutritionalProfileFactory for complex creation

---

## 📦 Domain Model

### Core Entities

#### 1. NutritionalProfile (Aggregate Root)

**Responsabilità:**
- Gestire dati utente (peso, altezza, età, sesso, livello attività)
- Calcolare e memorizzare BMR, TDEE, target calorico
- Distribuire macronutrienti per obiettivo (cut/maintain/bulk)
- Tracciare storico peso e progresso
- Validare invarianti di dominio

**Attributi:**
```python
@dataclass
class NutritionalProfile:
    profile_id: ProfileId              # UUID univoco
    user_id: str                       # Reference to user
    user_data: UserData                # Weight, height, age, sex, activity
    goal: Goal                         # cut, maintain, bulk
    bmr: BMR                           # Basal Metabolic Rate
    tdee: TDEE                         # Total Daily Energy Expenditure
    calories_target: CaloriesTarget    # Adjusted for goal
    macro_split: MacroSplit            # Protein, carbs, fat (grams)
    progress_history: list[ProgressRecord]  # Weight tracking
    created_at: Timestamp
    updated_at: Timestamp
```

**Metodi Business Logic:**
```python
def update_goal(self, new_goal: Goal) -> None:
    """Aggiorna obiettivo e ricalcola TDEE/macros"""
    
def record_progress(
    self, 
    weight: Weight, 
    date: Date,
    consumed_calories: Optional[float]
) -> ProgressRecord:
    """Registra peso e calorie consumate"""
    
def calculate_progress_score(self) -> ProgressScore:
    """Calcola score rispetto a obiettivo"""
    
def validate_invariants(self) -> None:
    """Valida: weight > 0, age 18-120, BMR > 0, etc."""
```

**Domain Events:**
- `ProfileCreated` - Quando profilo creato
- `ProfileUpdated` - Quando goal/user_data cambiano
- `ProgressRecorded` - Quando registrato peso/calorie

---

#### 2. ProgressRecord (Entity)

**Responsabilità:**
- Tracciare singola misurazione peso
- Memorizzare calorie consumate (da meals domain)
- Calcolare delta rispetto a target

**Attributi:**
```python
@dataclass
class ProgressRecord:
    record_id: RecordId                # UUID
    profile_id: ProfileId              # FK to NutritionalProfile
    date: Date                         # Data misurazione
    weight: Weight                     # Peso misurato (kg)
    consumed_calories: Optional[float] # Calorie da meals (optional)
    tdee_estimate: Optional[float]     # TDEE adattivo (Step 2 ML)
    notes: Optional[str]               # Note utente
    created_at: Timestamp
```

---

### Value Objects

#### 1. UserData

**Validazione:**
- `weight`: 30.0-300.0 kg (float)
- `height`: 100.0-250.0 cm (float)
- `age`: 18-120 anni (int)
- `sex`: 'M' o 'F' (Literal)
- `activity_level`: sedentary, light, moderate, active, very_active

```python
@dataclass(frozen=True)
class UserData:
    weight: float          # kg
    height: float          # cm
    age: int               # years
    sex: Literal['M', 'F']
    activity_level: ActivityLevel
    
    def __post_init__(self) -> None:
        if not (30.0 <= self.weight <= 300.0):
            raise InvalidUserDataError("Weight must be 30-300 kg")
        if not (100.0 <= self.height <= 250.0):
            raise InvalidUserDataError("Height must be 100-250 cm")
        if not (18 <= self.age <= 120):
            raise InvalidUserDataError("Age must be 18-120 years")
```

---

#### 2. Goal

**Valori:**
- `cut`: Deficit calorico (~-500 kcal/day)
- `maintain`: TDEE senza modifiche
- `bulk`: Surplus calorico (~+300 kcal/day)

```python
class Goal(str, Enum):
    CUT = "cut"
    MAINTAIN = "maintain"
    BULK = "bulk"
    
    def calorie_adjustment(self, tdee: float) -> float:
        """Applica deficit/surplus a TDEE"""
        adjustments = {
            Goal.CUT: -500,
            Goal.MAINTAIN: 0,
            Goal.BULK: +300
        }
        return tdee + adjustments[self]
```

---

#### 3. ActivityLevel

**PAL Multipliers (Physical Activity Level):**
- `sedentary`: 1.2 (lavoro sedentario, no esercizio)
- `light`: 1.375 (esercizio leggero 1-3 giorni/settimana)
- `moderate`: 1.55 (esercizio moderato 3-5 giorni/settimana)
- `active`: 1.725 (esercizio intenso 6-7 giorni/settimana)
- `very_active`: 1.9 (esercizio molto intenso + lavoro fisico)

```python
class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"
    
    def pal_multiplier(self) -> float:
        """Restituisce moltiplicatore PAL"""
        multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHT: 1.375,
            ActivityLevel.MODERATE: 1.55,
            ActivityLevel.ACTIVE: 1.725,
            ActivityLevel.VERY_ACTIVE: 1.9
        }
        return multipliers[self]
```

---

#### 4. BMR (Basal Metabolic Rate)

```python
@dataclass(frozen=True)
class BMR:
    value: float  # kcal/day
    
    def __post_init__(self) -> None:
        if self.value <= 0:
            raise InvalidBMRError("BMR must be positive")
```

---

#### 5. TDEE (Total Daily Energy Expenditure)

```python
@dataclass(frozen=True)
class TDEE:
    value: float  # kcal/day
    
    def __post_init__(self) -> None:
        if self.value <= 0:
            raise InvalidTDEEError("TDEE must be positive")
```

---

#### 6. MacroSplit

**Distribuzione macronutrienti in grammi:**

```python
@dataclass(frozen=True)
class MacroSplit:
    protein_g: int      # grammi proteine
    carbs_g: int        # grammi carboidrati
    fat_g: int          # grammi grassi
    
    def total_calories(self) -> float:
        """Calcola calorie totali (4/4/9 kcal/g)"""
        return (self.protein_g * 4) + (self.carbs_g * 4) + (self.fat_g * 9)
    
    def protein_percentage(self) -> float:
        """% calorie da proteine"""
        return (self.protein_g * 4) / self.total_calories() * 100
    
    def carbs_percentage(self) -> float:
        """% calorie da carboidrati"""
        return (self.carbs_g * 4) / self.total_calories() * 100
    
    def fat_percentage(self) -> float:
        """% calorie da grassi"""
        return (self.fat_g * 9) / self.total_calories() * 100
```

---

### Domain Services

#### 1. BMRService

**Formula: Mifflin-St Jeor**

```python
class BMRService:
    """Calcola Basal Metabolic Rate"""
    
    def calculate(self, user_data: UserData) -> BMR:
        """
        Uomini: 10 × peso + 6.25 × altezza - 5 × età + 5
        Donne:  10 × peso + 6.25 × altezza - 5 × età - 161
        """
        base = (
            10 * user_data.weight +
            6.25 * user_data.height -
            5 * user_data.age
        )
        
        if user_data.sex == 'M':
            bmr_value = base + 5
        else:  # 'F'
            bmr_value = base - 161
        
        return BMR(value=bmr_value)
```

**Test Cases:**
```python
# Esempio: Uomo, 80kg, 180cm, 30 anni
# BMR = 10*80 + 6.25*180 - 5*30 + 5
#     = 800 + 1125 - 150 + 5
#     = 1780 kcal/day

# Esempio: Donna, 60kg, 165cm, 25 anni
# BMR = 10*60 + 6.25*165 - 5*25 - 161
#     = 600 + 1031.25 - 125 - 161
#     = 1345.25 kcal/day
```

---

#### 2. TDEEService

**Formula: BMR × PAL**

```python
class TDEEService:
    """Calcola Total Daily Energy Expenditure"""
    
    def calculate(self, bmr: BMR, activity_level: ActivityLevel) -> TDEE:
        """TDEE = BMR × PAL multiplier"""
        pal = activity_level.pal_multiplier()
        tdee_value = bmr.value * pal
        return TDEE(value=tdee_value)
```

**Test Cases:**
```python
# BMR = 1780 kcal, activity_level = moderate (1.55)
# TDEE = 1780 * 1.55 = 2759 kcal/day

# BMR = 1345 kcal, activity_level = light (1.375)
# TDEE = 1345 * 1.375 = 1849 kcal/day
```

---

#### 3. MacroService

**Distribuzione macronutrienti per obiettivo:**

```python
class MacroService:
    """Calcola distribuzione macronutrienti"""
    
    def calculate(
        self, 
        calories_target: float, 
        weight: float, 
        goal: Goal
    ) -> MacroSplit:
        """
        Strategia:
        - Cut: 2.2g protein/kg, 25% fat, resto carbs
        - Maintain: 1.8g protein/kg, 30% fat, resto carbs
        - Bulk: 2.0g protein/kg, 20% fat, resto carbs
        """
        # Proteine
        protein_multipliers = {
            Goal.CUT: 2.2,
            Goal.MAINTAIN: 1.8,
            Goal.BULK: 2.0
        }
        protein_g = round(weight * protein_multipliers[goal])
        protein_cal = protein_g * 4
        
        # Grassi
        fat_percentages = {
            Goal.CUT: 0.25,
            Goal.MAINTAIN: 0.30,
            Goal.BULK: 0.20
        }
        fat_cal = calories_target * fat_percentages[goal]
        fat_g = round(fat_cal / 9)
        
        # Carboidrati (rimanente)
        carb_cal = calories_target - (protein_cal + fat_cal)
        carbs_g = round(carb_cal / 4)
        
        return MacroSplit(
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g
        )
```

**Test Cases:**
```python
# Target: 2259 kcal (cut), weight: 80kg
# Protein: 80 * 2.2 = 176g → 704 kcal
# Fat: 2259 * 0.25 = 565 kcal → 63g
# Carbs: (2259 - 704 - 565) / 4 = 248g
# Verifica: 176*4 + 248*4 + 63*9 = 2259 kcal ✓
```

---

## 🔌 Ports (Domain Interfaces)

### IProfileRepository

```python
class IProfileRepository(Protocol):
    """Port per persistenza profili nutrizionali"""
    
    async def save(self, profile: NutritionalProfile) -> None:
        """Salva profilo (create o update)"""
        ...
    
    async def find_by_id(self, profile_id: ProfileId) -> Optional[NutritionalProfile]:
        """Recupera profilo per ID"""
        ...
    
    async def find_by_user_id(self, user_id: str) -> Optional[NutritionalProfile]:
        """Recupera profilo per user_id"""
        ...
    
    async def delete(self, profile_id: ProfileId) -> None:
        """Elimina profilo (soft delete)"""
        ...
```

---

### IBMRCalculator

```python
class IBMRCalculator(Protocol):
    """Port per calcolo BMR"""
    
    def calculate(self, user_data: UserData) -> BMR:
        """Calcola BMR con formula Mifflin-St Jeor"""
        ...
```

---

### ITDEECalculator

```python
class ITDEECalculator(Protocol):
    """Port per calcolo TDEE"""
    
    def calculate(self, bmr: BMR, activity_level: ActivityLevel) -> TDEE:
        """Calcola TDEE = BMR × PAL"""
        ...
```

---

### IMacroCalculator

```python
class IMacroCalculator(Protocol):
    """Port per calcolo macronutrienti"""
    
    def calculate(
        self, 
        calories_target: float, 
        weight: float, 
        goal: Goal
    ) -> MacroSplit:
        """Calcola distribuzione protein/carbs/fat"""
        ...
```

---

## 🎮 Application Layer (CQRS)

### Commands

#### 1. CreateProfileCommand

```python
@dataclass
class CreateProfileCommand:
    user_id: str
    weight: float
    height: float
    age: int
    sex: Literal['M', 'F']
    activity_level: str
    goal: str

class CreateProfileHandler:
    def __init__(
        self,
        repository: IProfileRepository,
        orchestrator: ProfileOrchestrator,
        event_bus: IEventBus
    ):
        self.repository = repository
        self.orchestrator = orchestrator
        self.event_bus = event_bus
    
    async def handle(self, command: CreateProfileCommand) -> ProfileId:
        # 1. Validazione: profilo già esistente?
        existing = await self.repository.find_by_user_id(command.user_id)
        if existing:
            raise ProfileAlreadyExistsError(command.user_id)
        
        # 2. Orchestrazione: calcolo BMR → TDEE → macros
        profile = await self.orchestrator.create_profile(
            user_id=command.user_id,
            user_data=UserData(...),
            goal=Goal(command.goal)
        )
        
        # 3. Persistenza
        await self.repository.save(profile)
        
        # 4. Evento
        await self.event_bus.publish(ProfileCreated(
            profile_id=profile.profile_id,
            user_id=profile.user_id,
            bmr=profile.bmr.value,
            tdee=profile.tdee.value
        ))
        
        return profile.profile_id
```

---

#### 2. UpdateProfileCommand

```python
@dataclass
class UpdateProfileCommand:
    profile_id: ProfileId
    weight: Optional[float] = None
    activity_level: Optional[str] = None
    goal: Optional[str] = None

class UpdateProfileHandler:
    async def handle(self, command: UpdateProfileCommand) -> None:
        # 1. Recupera profilo
        profile = await self.repository.find_by_id(command.profile_id)
        if not profile:
            raise ProfileNotFoundError(command.profile_id)
        
        # 2. Aggiorna dati
        updated_fields = []
        if command.weight:
            profile.user_data.weight = command.weight
            updated_fields.append("weight")
        
        if command.goal:
            profile.update_goal(Goal(command.goal))
            updated_fields.append("goal")
        
        # 3. Ricalcola se necessario
        if updated_fields:
            profile = await self.orchestrator.recalculate_profile(profile)
        
        # 4. Salva
        await self.repository.save(profile)
        
        # 5. Evento
        await self.event_bus.publish(ProfileUpdated(
            profile_id=profile.profile_id,
            updated_fields=updated_fields
        ))
```

---

#### 3. RecordProgressCommand

```python
@dataclass
class RecordProgressCommand:
    profile_id: ProfileId
    weight: float
    date: Date
    consumed_calories: Optional[float] = None

class RecordProgressHandler:
    async def handle(self, command: RecordProgressCommand) -> RecordId:
        # 1. Recupera profilo
        profile = await self.repository.find_by_id(command.profile_id)
        if not profile:
            raise ProfileNotFoundError(command.profile_id)
        
        # 2. Registra progresso
        record = profile.record_progress(
            weight=Weight(command.weight),
            date=command.date,
            consumed_calories=command.consumed_calories
        )
        
        # 3. Salva profilo aggiornato
        await self.repository.save(profile)
        
        # 4. Evento
        await self.event_bus.publish(ProgressRecorded(
            profile_id=profile.profile_id,
            record_id=record.record_id,
            weight=record.weight.value,
            date=record.date
        ))
        
        return record.record_id
```

---

### Queries

#### 1. GetProfileQuery

```python
@dataclass
class GetProfileQuery:
    user_id: str

class GetProfileHandler:
    async def handle(self, query: GetProfileQuery) -> Optional[NutritionalProfile]:
        return await self.repository.find_by_user_id(query.user_id)
```

---

#### 2. CalculateProgressQuery

```python
@dataclass
class CalculateProgressQuery:
    profile_id: ProfileId
    start_date: Date
    end_date: Date

@dataclass
class ProgressScore:
    weight_delta: float          # kg persi/guadagnati
    target_delta: float          # obiettivo per periodo
    progress_percentage: float   # % completamento
    avg_daily_calories: float    # media calorie consumate
    days_on_track: int           # giorni entro ±10% target

class CalculateProgressHandler:
    async def handle(self, query: CalculateProgressQuery) -> ProgressScore:
        # 1. Recupera profilo
        profile = await self.repository.find_by_id(query.profile_id)
        if not profile:
            raise ProfileNotFoundError(query.profile_id)
        
        # 2. Filtra progress records nel range
        records = [
            r for r in profile.progress_history
            if query.start_date <= r.date <= query.end_date
        ]
        
        if not records:
            raise NoProgressDataError(query.profile_id, query.start_date, query.end_date)
        
        # 3. Calcola metriche
        first_weight = records[0].weight.value
        last_weight = records[-1].weight.value
        weight_delta = last_weight - first_weight
        
        # Target delta per goal
        days = (query.end_date - query.start_date).days
        if profile.goal == Goal.CUT:
            target_delta = -(500 / 7700) * days  # -0.5kg/week
        elif profile.goal == Goal.BULK:
            target_delta = (300 / 7700) * days   # +0.25kg/week
        else:
            target_delta = 0
        
        progress_percentage = (weight_delta / target_delta * 100) if target_delta != 0 else 100
        
        # Media calorie
        calories_records = [r.consumed_calories for r in records if r.consumed_calories]
        avg_daily_calories = sum(calories_records) / len(calories_records) if calories_records else 0
        
        # Giorni on track (±10% target)
        target = profile.calories_target.value
        days_on_track = sum(
            1 for r in records
            if r.consumed_calories and abs(r.consumed_calories - target) <= target * 0.1
        )
        
        return ProgressScore(
            weight_delta=weight_delta,
            target_delta=target_delta,
            progress_percentage=progress_percentage,
            avg_daily_calories=avg_daily_calories,
            days_on_track=days_on_track
        )
```

---

### Orchestrators

#### ProfileOrchestrator

**Responsabilità:**
- Coordinare servizi di calcolo (BMR → TDEE → Macros)
- Gestire workflow complessi
- Evitare accoppiamento tra command handlers e domain services

```python
class ProfileOrchestrator:
    def __init__(
        self,
        bmr_calculator: IBMRCalculator,
        tdee_calculator: ITDEECalculator,
        macro_calculator: IMacroCalculator,
        factory: NutritionalProfileFactory
    ):
        self.bmr_calculator = bmr_calculator
        self.tdee_calculator = tdee_calculator
        self.macro_calculator = macro_calculator
        self.factory = factory
    
    async def create_profile(
        self,
        user_id: str,
        user_data: UserData,
        goal: Goal
    ) -> NutritionalProfile:
        """Workflow: UserData → BMR → TDEE → Macros → Profile"""
        
        # 1. Calcola BMR
        bmr = self.bmr_calculator.calculate(user_data)
        
        # 2. Calcola TDEE
        tdee = self.tdee_calculator.calculate(bmr, user_data.activity_level)
        
        # 3. Applica adjustment per goal
        calories_target = goal.calorie_adjustment(tdee.value)
        
        # 4. Calcola macros
        macro_split = self.macro_calculator.calculate(
            calories_target=calories_target,
            weight=user_data.weight,
            goal=goal
        )
        
        # 5. Factory crea profilo
        profile = self.factory.create(
            user_id=user_id,
            user_data=user_data,
            goal=goal,
            bmr=bmr,
            tdee=tdee,
            calories_target=CaloriesTarget(calories_target),
            macro_split=macro_split
        )
        
        return profile
    
    async def recalculate_profile(
        self,
        profile: NutritionalProfile
    ) -> NutritionalProfile:
        """Ricalcola BMR/TDEE/Macros dopo update"""
        
        # Stesso workflow di create_profile
        bmr = self.bmr_calculator.calculate(profile.user_data)
        tdee = self.tdee_calculator.calculate(bmr, profile.user_data.activity_level)
        calories_target = profile.goal.calorie_adjustment(tdee.value)
        macro_split = self.macro_calculator.calculate(
            calories_target=calories_target,
            weight=profile.user_data.weight,
            goal=profile.goal
        )
        
        # Aggiorna profilo esistente
        profile.bmr = bmr
        profile.tdee = tdee
        profile.calories_target = CaloriesTarget(calories_target)
        profile.macro_split = macro_split
        profile.updated_at = Timestamp.now()
        
        return profile
```

---

## 🌐 GraphQL API

### Schema

```graphql
# Types
type NutritionalProfile {
  profileId: ID!
  userId: String!
  userData: UserData!
  goal: Goal!
  bmr: Float!
  tdee: Float!
  caloriesTarget: Float!
  macroSplit: MacroSplit!
  progressHistory: [ProgressRecord!]!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type UserData {
  weight: Float!      # kg
  height: Float!      # cm
  age: Int!
  sex: Sex!
  activityLevel: ActivityLevel!
}

enum Sex {
  M
  F
}

enum ActivityLevel {
  SEDENTARY
  LIGHT
  MODERATE
  ACTIVE
  VERY_ACTIVE
}

enum Goal {
  CUT
  MAINTAIN
  BULK
}

type MacroSplit {
  proteinG: Int!
  carbsG: Int!
  fatG: Int!
  totalCalories: Float!
  proteinPercentage: Float!
  carbsPercentage: Float!
  fatPercentage: Float!
}

type ProgressRecord {
  recordId: ID!
  profileId: ID!
  date: Date!
  weight: Float!
  consumedCalories: Float
  tdeeEstimate: Float
  notes: String
  createdAt: DateTime!
}

type ProgressScore {
  weightDelta: Float!
  targetDelta: Float!
  progressPercentage: Float!
  avgDailyCalories: Float!
  daysOnTrack: Int!
}

# Inputs
input CreateProfileInput {
  userId: String!
  weight: Float!
  height: Float!
  age: Int!
  sex: Sex!
  activityLevel: ActivityLevel!
  goal: Goal!
}

input UpdateProfileInput {
  profileId: ID!
  weight: Float
  activityLevel: ActivityLevel
  goal: Goal
}

input RecordProgressInput {
  profileId: ID!
  weight: Float!
  date: Date!
  consumedCalories: Float
}

# Mutations
type Mutation {
  createNutritionalProfile(input: CreateProfileInput!): NutritionalProfile!
  updateNutritionalProfile(input: UpdateProfileInput!): NutritionalProfile!
  recordProgress(input: RecordProgressInput!): ProgressRecord!
}

# Queries
type Query {
  nutritionalProfile(userId: String!): NutritionalProfile
  progressScore(profileId: ID!, startDate: Date!, endDate: Date!): ProgressScore!
}
```

---

### Resolver Implementation

```python
import strawberry
from application.nutritional_profile.commands import (
    CreateProfileCommand,
    UpdateProfileCommand,
    RecordProgressCommand
)
from application.nutritional_profile.queries import (
    GetProfileQuery,
    CalculateProgressQuery
)

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_nutritional_profile(
        self,
        input: CreateProfileInput,
        info: strawberry.Info
    ) -> NutritionalProfile:
        command_handler = info.context["create_profile_handler"]
        command = CreateProfileCommand(
            user_id=input.user_id,
            weight=input.weight,
            height=input.height,
            age=input.age,
            sex=input.sex.value,
            activity_level=input.activity_level.value,
            goal=input.goal.value
        )
        profile_id = await command_handler.handle(command)
        
        # Retrieve created profile
        query_handler = info.context["get_profile_handler"]
        profile = await query_handler.handle(GetProfileQuery(user_id=input.user_id))
        return profile

    @strawberry.mutation
    async def record_progress(
        self,
        input: RecordProgressInput,
        info: strawberry.Info
    ) -> ProgressRecord:
        command_handler = info.context["record_progress_handler"]
        command = RecordProgressCommand(
            profile_id=ProfileId.from_string(input.profile_id),
            weight=input.weight,
            date=input.date,
            consumed_calories=input.consumed_calories
        )
        record_id = await command_handler.handle(command)
        
        # Retrieve record from profile
        query_handler = info.context["get_profile_handler"]
        profile = await query_handler.handle(GetProfileQuery(user_id=...))
        record = next(r for r in profile.progress_history if r.record_id == record_id)
        return record

@strawberry.type
class Query:
    @strawberry.field
    async def nutritional_profile(
        self,
        user_id: str,
        info: strawberry.Info
    ) -> Optional[NutritionalProfile]:
        query_handler = info.context["get_profile_handler"]
        return await query_handler.handle(GetProfileQuery(user_id=user_id))
    
    @strawberry.field
    async def progress_score(
        self,
        profile_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
        info: strawberry.Info
    ) -> ProgressScore:
        query_handler = info.context["calculate_progress_handler"]
        return await query_handler.handle(CalculateProgressQuery(
            profile_id=ProfileId.from_string(profile_id),
            start_date=start_date,
            end_date=end_date
        ))
```

---

## 🔗 Integration with Meal/Activity Domains

### Cross-Domain Queries

**Scenario:** `progressScore` query deve recuperare calorie consumate da meals.

**Approccio 1: Repository Facade (RECOMMENDED)**

```python
class MealDataFacade:
    """Facade per accesso dati meal domain"""
    
    def __init__(self, meal_repository: IMealRepository):
        self.meal_repository = meal_repository
    
    async def get_consumed_calories_by_date_range(
        self,
        user_id: str,
        start_date: Date,
        end_date: Date
    ) -> dict[Date, float]:
        """Restituisce dict {date: total_calories}"""
        meals = await self.meal_repository.list_by_user_and_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        calories_by_date: dict[Date, float] = {}
        for meal in meals:
            date = meal.timestamp.date()
            if date not in calories_by_date:
                calories_by_date[date] = 0.0
            calories_by_date[date] += meal.total_calories
        
        return calories_by_date

# Usage in ProgressScoreHandler
class CalculateProgressHandler:
    def __init__(
        self,
        profile_repository: IProfileRepository,
        meal_facade: MealDataFacade  # ← Dependency injection
    ):
        self.profile_repository = profile_repository
        self.meal_facade = meal_facade
    
    async def handle(self, query: CalculateProgressQuery) -> ProgressScore:
        profile = await self.profile_repository.find_by_id(query.profile_id)
        
        # Recupera calorie consumate da meal domain
        calories_by_date = await self.meal_facade.get_consumed_calories_by_date_range(
            user_id=profile.user_id,
            start_date=query.start_date,
            end_date=query.end_date
        )
        
        # Arricchisci progress records con calorie
        for record in profile.progress_history:
            if record.date in calories_by_date:
                record.consumed_calories = calories_by_date[record.date]
        
        # ... resto del calcolo
```

**Approccio 2: Domain Events (Alternative)**

```python
# Meal domain emette evento
@dataclass
class MealConfirmedEvent:
    meal_id: MealId
    user_id: str
    timestamp: Timestamp
    total_calories: float

# Nutritional profile domain ascolta evento
class MealConfirmedEventHandler:
    async def handle(self, event: MealConfirmedEvent) -> None:
        # Recupera profilo utente
        profile = await self.repository.find_by_user_id(event.user_id)
        if not profile:
            return
        
        # Cerca progress record per data
        date = event.timestamp.date()
        record = next(
            (r for r in profile.progress_history if r.date == date),
            None
        )
        
        if record:
            # Aggiorna calorie consumate (cumulativo)
            record.consumed_calories = (record.consumed_calories or 0) + event.total_calories
            await self.repository.save(profile)
```

**Raccomandazione:** Usa **Repository Facade** per query sincrone, **Domain Events** per aggiornamenti asincroni.

---

## 🧪 Testing Strategy

### Unit Tests (Domain Layer)

**Value Objects:**
```python
def test_user_data_validation():
    # Valid
    data = UserData(weight=70.0, height=175.0, age=30, sex='M', activity_level=ActivityLevel.MODERATE)
    assert data.weight == 70.0
    
    # Invalid weight
    with pytest.raises(InvalidUserDataError):
        UserData(weight=25.0, ...)  # < 30 kg

def test_goal_calorie_adjustment():
    goal = Goal.CUT
    tdee = 2500.0
    adjusted = goal.calorie_adjustment(tdee)
    assert adjusted == 2000.0  # -500
```

**Services:**
```python
def test_bmr_service_male():
    service = BMRService()
    user_data = UserData(weight=80.0, height=180.0, age=30, sex='M', activity_level=ActivityLevel.MODERATE)
    bmr = service.calculate(user_data)
    assert bmr.value == 1780.0  # 10*80 + 6.25*180 - 5*30 + 5

def test_tdee_service():
    service = TDEEService()
    bmr = BMR(value=1780.0)
    activity_level = ActivityLevel.MODERATE
    tdee = service.calculate(bmr, activity_level)
    assert tdee.value == 2759.0  # 1780 * 1.55
```

---

### Integration Tests (Infrastructure)

**Repository:**
```python
@pytest.mark.integration
async def test_mongo_profile_repository_save_and_retrieve():
    repository = MongoProfileRepository(db)
    
    profile = NutritionalProfileFactory.create(
        user_id="user123",
        user_data=UserData(...),
        goal=Goal.CUT
    )
    
    await repository.save(profile)
    
    retrieved = await repository.find_by_user_id("user123")
    assert retrieved.profile_id == profile.profile_id
    assert retrieved.bmr.value == profile.bmr.value
```

---

### E2E Tests (GraphQL)

**Complete Workflow:**
```python
@pytest.mark.e2e
async def test_create_profile_workflow():
    # 1. Create profile
    mutation = """
    mutation {
      createNutritionalProfile(input: {
        userId: "user123"
        weight: 80.0
        height: 180.0
        age: 30
        sex: M
        activityLevel: MODERATE
        goal: CUT
      }) {
        profileId
        bmr
        tdee
        caloriesTarget
        macroSplit {
          proteinG
          carbsG
          fatG
        }
      }
    }
    """
    result = await execute_graphql(mutation)
    assert result["createNutritionalProfile"]["bmr"] == 1780.0
    assert result["createNutritionalProfile"]["tdee"] == 2759.0
    assert result["createNutritionalProfile"]["caloriesTarget"] == 2259.0
    
    # 2. Record progress
    mutation = """
    mutation {
      recordProgress(input: {
        profileId: "{profile_id}"
        weight: 79.5
        date: "2025-11-01"
        consumedCalories: 2250.0
      }) {
        recordId
        weight
      }
    }
    """
    result = await execute_graphql(mutation)
    assert result["recordProgress"]["weight"] == 79.5
    
    # 3. Calculate progress
    query = """
    query {
      progressScore(profileId: "{profile_id}", startDate: "2025-11-01", endDate: "2025-11-07") {
        weightDelta
        progressPercentage
        daysOnTrack
      }
    }
    """
    result = await execute_graphql(query)
    assert result["progressScore"]["weightDelta"] < 0  # Peso perso
```

---

## 📝 Implementation Checklist

### Phase 9.1: Setup Dependencies
- [ ] Add `numpy>=1.26.0` to pyproject.toml
- [ ] Run `uv sync`
- [ ] Test imports

### Phase 9.2: Domain Core
- [ ] Value objects: UserData, Goal, ActivityLevel, BMR, TDEE, MacroSplit
- [ ] Entities: NutritionalProfile, ProgressRecord
- [ ] Events: ProfileCreated, ProfileUpdated, ProgressRecorded
- [ ] Exceptions: ProfileDomainError hierarchy
- [ ] Ports: IProfileRepository, IBMRCalculator, ITDEECalculator, IMacroCalculator
- [ ] Factory: NutritionalProfileFactory
- [ ] Unit tests (>90% coverage)

### Phase 9.3: Calculation Services
- [ ] BMRService (Mifflin-St Jeor)
- [ ] TDEEService (PAL multipliers)
- [ ] MacroService (protein/carbs/fat)
- [ ] Unit tests (deterministic)

### Phase 9.4: Application Layer
- [ ] CreateProfileCommand + Handler
- [ ] UpdateProfileCommand + Handler
- [ ] RecordProgressCommand + Handler
- [ ] GetProfileQuery + Handler
- [ ] CalculateProgressQuery + Handler
- [ ] ProfileOrchestrator
- [ ] Unit tests (mock repositories)

### Phase 9.5: Infrastructure
- [ ] MongoProfileRepository
- [ ] BMRCalculatorAdapter
- [ ] TDEECalculatorAdapter
- [ ] MacroCalculatorAdapter
- [ ] MealDataFacade (cross-domain)
- [ ] Integration tests

### Phase 9.6: GraphQL Layer
- [ ] Strawberry types (NutritionalProfileType, etc.)
- [ ] Mutations (create, update, recordProgress)
- [ ] Queries (nutritionalProfile, progressScore)
- [ ] Schema integration
- [ ] E2E tests

### Phase 9.7: Testing & Quality
- [ ] Unit test coverage >90%
- [ ] Integration tests (cross-domain)
- [ ] E2E script (test_nutritional_profile.sh)
- [ ] Documentation
- [ ] Commit MVP

---

## 🚀 Next Steps (Step 2 & 3 - Deferred)

### Step 2: ML Enhancement
- Kalman filter per TDEE adattivo
- Prophet forecasting peso futuro
- Weekly ML pipeline
- Dependencies: statsmodels, scipy, pandas

### Step 3: LLM Feedback
- OpenAI feedback motivazionale
- Prompt engineering
- Cost optimization (caching)
- Weekly feedback generation

---

**Document Version:** 1.0  
**Last Updated:** 30 Ottobre 2025  
**Next Review:** After MVP implementation (Phase 9.7)
