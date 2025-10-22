# 🌐 GraphQL API - Complete Schema & Resolvers

**Data:** 22 Ottobre 2025  
**Layer:** GraphQL (Presentation)  
**Dependencies:** Application Layer (Commands, Queries, Orchestrators)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Complete Schema](#complete-schema)
3. [Mutations](#mutations)
4. [Queries](#queries)
5. [Types](#types)
6. [Resolvers](#resolvers)
7. [Error Handling](#error-handling)
8. [SpectaQL Documentation](#spectaql-documentation)
9. [Examples](#examples)

---

## 🎯 Overview

### GraphQL API Design Principles

- ✅ **Query-first**: Design schema from client needs
- ✅ **Explicit errors**: Use Union types for error handling
- ✅ **Pagination**: Cursor-based for large lists
- ✅ **Nullability**: Be explicit about required fields
- ✅ **Documentation**: Every field has description

### API Endpoints

**Production**: `https://api.nutrifit.app/graphql`  
**Staging**: `https://staging.nutrifit.app/graphql`  
**Local**: `http://localhost:8000/graphql`

---

## 📐 Complete Schema

```graphql
# schema.graphql
"""
Nutrifit Meal Domain API v2.0

Complete API for meal photo recognition, barcode scanning,
and nutrition tracking.
"""

schema {
  query: Query
  mutation: Mutation
}

# ============================================
# ROOT OPERATIONS
# ============================================

type Query {
  """Get single meal by ID"""
  meal(id: ID!): MealResult!
  
  """List user meals with filters"""
  mealHistory(
    userId: String!
    startDate: DateTime
    endDate: DateTime
    mealType: MealType
    limit: Int = 20
    offset: Int = 0
  ): MealHistoryResult!
  
  """Search meals by text"""
  searchMeals(
    userId: String!
    query: String!
    limit: Int = 20
  ): MealSearchResult!
  
  """Get daily nutrition summary"""
  dailySummary(
    userId: String!
    date: Date!
  ): DailySummaryResult!
  
  """Atomic: Recognize food from photo (utility)"""
  recognizeFood(
    photoUrl: String!
    hint: String
  ): RecognitionResult!
  
  """Atomic: Enrich nutrients from USDA (utility)"""
  enrichNutrients(
    label: String!
    quantityG: Float!
  ): NutrientProfile
  
  """Atomic: Lookup product by barcode (utility)"""
  searchFoodByBarcode(
    barcode: String!
  ): BarcodeProduct
}

type Mutation {
  """Analyze meal from photo"""
  analyzeMealPhoto(
    input: PhotoAnalysisInput!
  ): MealAnalysisResult!
  
  """Analyze meal from barcode"""
  analyzeMealBarcode(
    input: BarcodeAnalysisInput!
  ): MealAnalysisResult!
  
  """Analyze meal from text description"""
  analyzeMealDescription(
    input: TextAnalysisInput!
  ): MealAnalysisResult!
  
  """Confirm meal analysis (2-step process)"""
  confirmMealAnalysis(
    input: ConfirmAnalysisInput!
  ): ConfirmationResult!
  
  """Update meal"""
  updateMeal(
    input: UpdateMealInput!
  ): MealUpdateResult!
  
  """Delete meal (soft delete)"""
  deleteMeal(
    id: ID!
    userId: String!
  ): DeleteResult!
}

# ============================================
# INPUT TYPES
# ============================================

input PhotoAnalysisInput {
  """User ID"""
  userId: String!
  
  """Photo URL (already uploaded to storage)"""
  photoUrl: String!
  
  """Optional hint (e.g., 'carbonara')"""
  dishHint: String
  
  """Meal type (breakfast, lunch, dinner, snack)"""
  mealType: MealType = LUNCH
  
  """Timestamp (defaults to now)"""
  timestamp: DateTime
}

input BarcodeAnalysisInput {
  """User ID"""
  userId: String!
  
  """Barcode (EAN/UPC)"""
  barcode: String!
  
  """Quantity in grams"""
  quantityG: Float!
  
  """Meal type"""
  mealType: MealType = SNACK
  
  """Timestamp"""
  timestamp: DateTime
}

input TextAnalysisInput {
  """User ID"""
  userId: String!
  
  """Text description (e.g., 'pasta al pomodoro e insalata')"""
  description: String!
  
  """Meal type"""
  mealType: MealType = LUNCH
  
  """Timestamp"""
  timestamp: DateTime
}

input ConfirmAnalysisInput {
  """Meal ID to confirm"""
  mealId: ID!
  
  """User ID (ownership check)"""
  userId: String!
  
  """Entry IDs to keep (others discarded)"""
  confirmedEntryIds: [ID!]!
}

input UpdateMealInput {
  """Meal ID"""
  mealId: ID!
  
  """User ID (ownership check)"""
  userId: String!
  
  """New dish name (optional)"""
  dishName: String
  
  """New meal type (optional)"""
  mealType: MealType
  
  """Entry updates"""
  entryUpdates: [EntryUpdate!]
}

input EntryUpdate {
  """Entry ID"""
  entryId: ID!
  
  """New quantity (optional)"""
  quantityG: Float
  
  """New display name (optional)"""
  displayName: String
}

# ============================================
# ENUMS
# ============================================

enum MealType {
  BREAKFAST
  LUNCH
  DINNER
  SNACK
}

enum AnalysisType {
  PHOTO
  BARCODE
  TEXT
}

# ============================================
# RESULT TYPES (Union for errors)
# ============================================

union MealAnalysisResult = MealAnalysisSuccess | MealAnalysisError

type MealAnalysisSuccess {
  """Created meal"""
  meal: Meal!
  
  """Processing time (ms)"""
  processingTimeMs: Int!
  
  """Warnings (if any)"""
  warnings: [String!]!
}

type MealAnalysisError {
  """Error code"""
  code: ErrorCode!
  
  """Error message"""
  message: String!
  
  """Detailed errors (field-level)"""
  details: [ErrorDetail!]
}

union ConfirmationResult = ConfirmationSuccess | ConfirmationError

type ConfirmationSuccess {
  """Confirmed meal"""
  meal: Meal!
}

type ConfirmationError {
  code: ErrorCode!
  message: String!
}

union MealUpdateResult = MealUpdateSuccess | MealUpdateError

type MealUpdateSuccess {
  meal: Meal!
}

type MealUpdateError {
  code: ErrorCode!
  message: String!
}

union DeleteResult = DeleteSuccess | DeleteError

type DeleteSuccess {
  """Deleted meal ID"""
  mealId: ID!
  
  """Success message"""
  message: String!
}

type DeleteError {
  code: ErrorCode!
  message: String!
}

union MealResult = Meal | MealNotFoundError

type MealNotFoundError {
  mealId: ID!
  message: String!
}

union MealHistoryResult = MealHistorySuccess | MealHistoryError

type MealHistorySuccess {
  """Meals"""
  meals: [Meal!]!
  
  """Total count (for pagination)"""
  totalCount: Int!
  
  """Has more results"""
  hasMore: Boolean!
}

type MealHistoryError {
  code: ErrorCode!
  message: String!
}

union MealSearchResult = MealSearchSuccess | MealSearchError

type MealSearchSuccess {
  meals: [Meal!]!
  totalCount: Int!
}

type MealSearchError {
  code: ErrorCode!
  message: String!
}

union DailySummaryResult = DailySummary | DailySummaryError

type DailySummaryError {
  code: ErrorCode!
  message: String!
}

# ============================================
# CORE TYPES
# ============================================

type Meal {
  """Meal ID"""
  id: ID!
  
  """User ID"""
  userId: String!
  
  """Dish name (e.g., 'Spaghetti alla Carbonara')"""
  dishName: String!
  
  """Meal entries (individual food items)"""
  entries: [MealEntry!]!
  
  """Analysis type"""
  analysisType: AnalysisType!
  
  """Meal type"""
  mealType: MealType!
  
  """Average confidence (0.0-1.0)"""
  confidence: Float!
  
  """Confirmed by user?"""
  confirmed: Boolean!
  
  """Timestamp"""
  timestamp: DateTime!
  
  """Confirmed at (if confirmed)"""
  confirmedAt: DateTime
  
  """Photo URL (if from photo/barcode)"""
  imageUrl: String
  
  """Total calories"""
  totalCalories: Int!
  
  """Total protein (g)"""
  totalProtein: Float!
  
  """Total carbs (g)"""
  totalCarbs: Float!
  
  """Total fat (g)"""
  totalFat: Float!
  
  """Created at"""
  createdAt: DateTime!
  
  """Updated at"""
  updatedAt: DateTime!
}

type MealEntry {
  """Entry ID"""
  id: ID!
  
  """USDA-compatible label"""
  label: String!
  
  """User-friendly name (Italian)"""
  displayName: String!
  
  """Quantity (g)"""
  quantityG: Float!
  
  """Confidence (0.0-1.0)"""
  confidence: Float!
  
  """Category (optional)"""
  category: String
  
  """Nutrients"""
  nutrients: NutrientProfile
  
  """Image URL (from barcode lookup)"""
  imageUrl: String
  
  """Barcode (if from barcode scan)"""
  barcode: String
}

type NutrientProfile {
  """Calories (kcal)"""
  calories: Int!
  
  """Protein (g)"""
  protein: Float!
  
  """Carbs (g)"""
  carbs: Float!
  
  """Fat (g)"""
  fat: Float!
  
  """Fiber (g, optional)"""
  fiber: Float
  
  """Sugar (g, optional)"""
  sugar: Float
  
  """Sodium (mg, optional)"""
  sodium: Float
  
  """Source (USDA, OpenFoodFacts, Estimated)"""
  source: String!
  
  """Confidence (0.0-1.0)"""
  confidence: Float!
  
  """Reference quantity (g)"""
  quantityG: Float!
}

type DailySummary {
  """Date"""
  date: Date!
  
  """User ID"""
  userId: String!
  
  """Total calories"""
  totalCalories: Int!
  
  """Total protein (g)"""
  totalProtein: Float!
  
  """Total carbs (g)"""
  totalCarbs: Float!
  
  """Total fat (g)"""
  totalFat: Float!
  
  """Meal count"""
  mealCount: Int!
  
  """Meals breakdown by type"""
  byMealType: [MealTypeBreakdown!]!
  
  """All meals"""
  meals: [Meal!]!
}

type MealTypeBreakdown {
  """Meal type"""
  mealType: MealType!
  
  """Calories"""
  calories: Int!
  
  """Meal count"""
  count: Int!
}

type RecognitionResult {
  """Dish title"""
  dishTitle: String!
  
  """Recognized items"""
  items: [RecognizedFood!]!
  
  """Average confidence"""
  confidence: Float!
  
  """Processing time (ms)"""
  processingTimeMs: Int!
}

type RecognizedFood {
  """USDA-compatible label"""
  label: String!
  
  """User-friendly name"""
  displayName: String!
  
  """Quantity (g)"""
  quantityG: Float!
  
  """Unit"""
  unit: String!
  
  """Confidence"""
  confidence: Float!
}

type BarcodeProduct {
  """Product name"""
  name: String!
  
  """Barcode"""
  barcode: String!
  
  """Brand (optional)"""
  brand: String
  
  """Category (optional)"""
  category: String
  
  """Image URL"""
  imageUrl: String!
  
  """Nutrients (per 100g)"""
  nutrients: NutrientProfile
}

# ============================================
# ERROR TYPES
# ============================================

enum ErrorCode {
  VALIDATION_ERROR
  NOT_FOUND
  UNAUTHORIZED
  EXTERNAL_API_ERROR
  CIRCUIT_BREAKER_OPEN
  RATE_LIMIT_EXCEEDED
  INTERNAL_ERROR
}

type ErrorDetail {
  """Field name"""
  field: String!
  
  """Error message"""
  message: String!
}

# ============================================
# SCALARS
# ============================================

"""ISO 8601 DateTime (e.g., '2025-10-22T10:30:00Z')"""
scalar DateTime

"""ISO 8601 Date (e.g., '2025-10-22')"""
scalar Date
```

---

## 🔧 Mutations

### 1. analyzeMealPhoto

**Purpose**: Recognize food from photo using OpenAI Vision + USDA enrichment

**Flow**:
1. User uploads photo to storage → gets `photoUrl`
2. Call `analyzeMealPhoto` with `photoUrl`
3. OpenAI Vision recognizes food items
4. USDA enriches each item with nutrients
5. MealFactory creates Meal (unconfirmed)
6. Repository saves Meal
7. Return `MealAnalysisSuccess` with Meal

**Example**:
```graphql
mutation AnalyzePhoto {
  analyzeMealPhoto(
    input: {
      userId: "user123"
      photoUrl: "https://storage.nutrifit.app/photos/abc123.jpg"
      dishHint: "carbonara"
      mealType: LUNCH
    }
  ) {
    ... on MealAnalysisSuccess {
      meal {
        id
        dishName
        confidence
        entries {
          id
          label
          displayName
          quantityG
          confidence
          nutrients {
            calories
            protein
            carbs
            fat
          }
        }
        totalCalories
      }
      processingTimeMs
      warnings
    }
    ... on MealAnalysisError {
      code
      message
      details {
        field
        message
      }
    }
  }
}
```

---

### 2. analyzeMealBarcode

**Purpose**: Lookup product by barcode (OpenFoodFacts) + USDA fallback

**Flow**:
1. User scans barcode → gets barcode string
2. Call `analyzeMealBarcode` with barcode + quantity
3. OpenFoodFacts lookup product
4. If nutrients available → use directly
5. Else → USDA fallback by category
6. MealFactory creates Meal with single entry
7. Repository saves Meal
8. Return `MealAnalysisSuccess`

**Example**:
```graphql
mutation AnalyzeBarcode {
  analyzeMealBarcode(
    input: {
      userId: "user123"
      barcode: "8001050000000"
      quantityG: 100
      mealType: SNACK
    }
  ) {
    ... on MealAnalysisSuccess {
      meal {
        id
        dishName
        entries {
          id
          displayName
          barcode
          imageUrl  # ⚠️ From OpenFoodFacts
          nutrients {
            calories
            source  # "OpenFoodFacts" or "USDA"
          }
        }
      }
    }
    ... on MealAnalysisError {
      code
      message
    }
  }
}
```

---

### 3. analyzeMealDescription

**Purpose**: Extract food items from text description

**Flow**:
1. User types "pasta al pomodoro e insalata"
2. Call `analyzeMealDescription`
3. OpenAI extracts structured food items
4. USDA enriches nutrients
5. MealFactory creates Meal
6. Repository saves Meal

**Example**:
```graphql
mutation AnalyzeText {
  analyzeMealDescription(
    input: {
      userId: "user123"
      description: "Petto di pollo alla griglia con insalata verde e patate bollite"
      mealType: DINNER
    }
  ) {
    ... on MealAnalysisSuccess {
      meal {
        id
        dishName
        entries {
          label  # "chicken breast, grilled"
          displayName  # "Petto di pollo alla griglia"
          quantityG
          nutrients {
            calories
          }
        }
      }
    }
  }
}
```

---

### 4. confirmMealAnalysis

**Purpose**: 2-step confirmation (user reviews AI results)

**Flow**:
1. User reviews unconfirmed meal
2. User selects entries to keep
3. Call `confirmMealAnalysis` with entry IDs
4. Domain validates and confirms Meal
5. Unselected entries removed
6. Repository updates Meal
7. Event published

**Example**:
```graphql
mutation ConfirmMeal {
  confirmMealAnalysis(
    input: {
      mealId: "meal_abc123"
      userId: "user123"
      confirmedEntryIds: ["entry_1", "entry_2"]  # Keep only these
    }
  ) {
    ... on ConfirmationSuccess {
      meal {
        id
        confirmed
        confirmedAt
        entries {
          id
          displayName
        }
      }
    }
    ... on ConfirmationError {
      code
      message
    }
  }
}
```

---

### 5. updateMeal

**Purpose**: Update meal after confirmation

**Flow**:
1. User edits dish name or entry quantities
2. Call `updateMeal`
3. Domain validates updates
4. Repository updates Meal
5. Event published

**Example**:
```graphql
mutation UpdateMeal {
  updateMeal(
    input: {
      mealId: "meal_abc123"
      userId: "user123"
      dishName: "Spaghetti Carbonara Modificata"
      entryUpdates: [
        {
          entryId: "entry_1"
          quantityG: 300  # Changed from 250g
        }
      ]
    }
  ) {
    ... on MealUpdateSuccess {
      meal {
        id
        dishName
        totalCalories  # Recalculated
      }
    }
  }
}
```

---

### 6. deleteMeal

**Purpose**: Soft delete meal

**Example**:
```graphql
mutation DeleteMeal {
  deleteMeal(
    id: "meal_abc123"
    userId: "user123"
  ) {
    ... on DeleteSuccess {
      mealId
      message
    }
    ... on DeleteError {
      code
      message
    }
  }
}
```

---

## 🔍 Queries

### 1. meal

**Purpose**: Get single meal by ID

**Example**:
```graphql
query GetMeal {
  meal(id: "meal_abc123") {
    ... on Meal {
      id
      dishName
      entries {
        displayName
        nutrients {
          calories
        }
      }
      totalCalories
    }
    ... on MealNotFoundError {
      mealId
      message
    }
  }
}
```

---

### 2. mealHistory

**Purpose**: List user meals with filters

**Example**:
```graphql
query MealHistory {
  mealHistory(
    userId: "user123"
    startDate: "2025-10-01T00:00:00Z"
    endDate: "2025-10-31T23:59:59Z"
    mealType: LUNCH
    limit: 20
    offset: 0
  ) {
    ... on MealHistorySuccess {
      meals {
        id
        dishName
        timestamp
        totalCalories
        confirmed
      }
      totalCount
      hasMore
    }
  }
}
```

---

### 3. dailySummary

**Purpose**: Daily nutrition aggregation

**Example**:
```graphql
query DailySummary {
  dailySummary(
    userId: "user123"
    date: "2025-10-22"
  ) {
    ... on DailySummary {
      date
      totalCalories
      totalProtein
      totalCarbs
      totalFat
      mealCount
      byMealType {
        mealType
        calories
        count
      }
      meals {
        id
        dishName
        mealType
        totalCalories
      }
    }
  }
}
```

---

### 4. recognizeFood (Atomic Utility)

**Purpose**: Test OpenAI recognition without saving

**Example**:
```graphql
query RecognizeFood {
  recognizeFood(
    photoUrl: "https://example.com/test.jpg"
    hint: "pasta"
  ) {
    dishTitle
    items {
      label
      displayName
      quantityG
      confidence
    }
    confidence
    processingTimeMs
  }
}
```

---

### 5. enrichNutrients (Atomic Utility)

**Purpose**: Test USDA enrichment

**Example**:
```graphql
query EnrichNutrients {
  enrichNutrients(
    label: "chicken breast, roasted"
    quantityG: 200
  ) {
    calories
    protein
    carbs
    fat
    source
    confidence
  }
}
```

---

### 6. searchFoodByBarcode (Atomic Utility)

**Purpose**: Test barcode lookup

**Example**:
```graphql
query SearchBarcode {
  searchFoodByBarcode(barcode: "8001050000000") {
    name
    brand
    imageUrl
    nutrients {
      calories
      protein
    }
  }
}
```

---

## 🏗️ Resolvers

### Strawberry Setup

```python
# graphql/schema.py
"""
GraphQL Schema with Strawberry

Wires GraphQL layer → Application layer
"""

import strawberry
from typing import List, Optional
from datetime import datetime, date

from .resolvers.meal_mutations import MealMutation
from .resolvers.meal_queries import MealQuery


@strawberry.type
class Query:
    """Root Query"""
    
    # Delegate to MealQuery
    meal: MealQuery.meal = strawberry.field(resolver=MealQuery.meal)
    meal_history: MealQuery.meal_history = strawberry.field(resolver=MealQuery.meal_history)
    daily_summary: MealQuery.daily_summary = strawberry.field(resolver=MealQuery.daily_summary)
    recognize_food: MealQuery.recognize_food = strawberry.field(resolver=MealQuery.recognize_food)
    enrich_nutrients: MealQuery.enrich_nutrients = strawberry.field(resolver=MealQuery.enrich_nutrients)
    search_food_by_barcode: MealQuery.search_food_by_barcode = strawberry.field(resolver=MealQuery.search_food_by_barcode)


@strawberry.type
class Mutation:
    """Root Mutation"""
    
    # Delegate to MealMutation
    analyze_meal_photo: MealMutation.analyze_meal_photo = strawberry.field(resolver=MealMutation.analyze_meal_photo)
    analyze_meal_barcode: MealMutation.analyze_meal_barcode = strawberry.field(resolver=MealMutation.analyze_meal_barcode)
    analyze_meal_description: MealMutation.analyze_meal_description = strawberry.field(resolver=MealMutation.analyze_meal_description)
    confirm_meal_analysis: MealMutation.confirm_meal_analysis = strawberry.field(resolver=MealMutation.confirm_meal_analysis)
    update_meal: MealMutation.update_meal = strawberry.field(resolver=MealMutation.update_meal)
    delete_meal: MealMutation.delete_meal = strawberry.field(resolver=MealMutation.delete_meal)


schema = strawberry.Schema(query=Query, mutation=Mutation)
```

---

### Example Resolver: analyzeMealPhoto

```python
# graphql/resolvers/meal_mutations.py
"""
Meal Mutations

Maps GraphQL mutations → Application commands
"""

import strawberry
from typing import Union
import structlog

from application.meal.commands.analyze_photo import (
    AnalyzeMealPhotoCommand,
    AnalyzeMealPhotoCommandHandler
)
from .types.meal import (
    PhotoAnalysisInput,
    MealAnalysisResult,
    MealAnalysisSuccess,
    MealAnalysisError,
    ErrorCode
)
from .mappers.meal_mapper import MealMapper

logger = structlog.get_logger(__name__)


@strawberry.type
class MealMutation:
    """Meal mutations"""
    
    @strawberry.mutation
    async def analyze_meal_photo(
        self,
        info: strawberry.Info,
        input: PhotoAnalysisInput
    ) -> MealAnalysisResult:
        """
        Analyze meal from photo.
        
        Flow:
        1. GraphQL input → Application command
        2. Handler executes command
        3. Domain result → GraphQL type
        """
        handler: AnalyzeMealPhotoCommandHandler = info.context["analyze_photo_handler"]
        
        logger.info(
            "graphql_analyze_photo",
            user_id=input.user_id,
            has_hint=input.dish_hint is not None
        )
        
        try:
            # Create command
            command = AnalyzeMealPhotoCommand(
                user_id=input.user_id,
                photo_url=input.photo_url,
                dish_hint=input.dish_hint,
                meal_type=input.meal_type.value if input.meal_type else "LUNCH",
                timestamp=input.timestamp
            )
            
            # Execute command
            result = await handler.handle(command)
            
            # Map domain → GraphQL
            meal_gql = MealMapper.to_graphql(result.meal)
            
            logger.info(
                "graphql_analyze_photo_success",
                meal_id=str(result.meal.id)
            )
            
            return MealAnalysisSuccess(
                meal=meal_gql,
                processing_time_ms=result.processing_time_ms,
                warnings=result.warnings
            )
            
        except ValueError as e:
            logger.warning("graphql_analyze_photo_validation_error", error=str(e))
            return MealAnalysisError(
                code=ErrorCode.VALIDATION_ERROR,
                message=str(e),
                details=[]
            )
            
        except Exception as e:
            logger.error("graphql_analyze_photo_error", error=str(e), exc_info=True)
            return MealAnalysisError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Internal error",
                details=[]
            )
```

---

## ⚠️ Error Handling

### Union Types for Type-Safe Errors

**❌ BAD** (nullable errors):
```graphql
type MealResult {
  meal: Meal
  error: String  # ❌ Not type-safe
}
```

**✅ GOOD** (union types):
```graphql
union MealAnalysisResult = MealAnalysisSuccess | MealAnalysisError

type MealAnalysisError {
  code: ErrorCode!
  message: String!
  details: [ErrorDetail!]
}
```

**Client handling**:
```typescript
const result = await analyzeMealPhoto({ ... });

if (result.__typename === 'MealAnalysisSuccess') {
  // Type-safe: result.meal exists
  console.log(result.meal.id);
} else {
  // Type-safe: result.code exists
  console.error(result.code, result.message);
}
```

---

## 📚 SpectaQL Documentation

### What is SpectaQL?

**SpectaQL** genera documentazione HTML interattiva dal GraphQL schema.

**Features**:
- ✅ Auto-generated from schema
- ✅ Interactive explorer
- ✅ Type navigation
- ✅ Examples
- ✅ Custom branding

---

### Installation

```bash
# Install SpectaQL
npm install -g spectaql

# Or use npx (no install)
npx spectaql
```

---

### Configuration

```yaml
# spectaql.yaml
"""
SpectaQL Configuration for Nutrifit Meal API

Generates interactive API documentation at:
backend/docs/REFACTOR/NEW/api/index.html
"""

spectaql:
  # Output directory
  targetDir: ./backend/docs/REFACTOR/NEW/api
  
  # Theme customization
  themeOverrides:
    primaryColor: '#4CAF50'      # Nutrifit green
    secondaryColor: '#FF9800'    # Orange accent
    fontFamily: 'Inter, system-ui, sans-serif'
  
  # Logo (optional)
  logoFile: ./docs/logo.png
  
  # Favicon
  faviconFile: ./docs/favicon.ico

introspection:
  # GraphQL schema file
  schemaFile: ./backend/graphql/schema.graphql
  
  # Or introspection URL (for running server)
  # url: http://localhost:8000/graphql
  # headers:
  #   Authorization: Bearer ${ADMIN_TOKEN}

info:
  # API info
  title: Nutrifit Meal API
  description: |
    # Nutrifit Meal Domain API v2.0
    
    Complete API for meal photo recognition, barcode scanning,
    and nutrition tracking.
    
    ## Features
    - 📸 AI-powered photo recognition (OpenAI Vision)
    - 🏷️ Barcode scanning (OpenFoodFacts)
    - 📝 Text-based meal logging
    - 🥗 USDA nutrition enrichment
    - 📊 Daily summaries & history
    
    ## Getting Started
    1. Upload photo to storage
    2. Call `analyzeMealPhoto` mutation
    3. Review results
    4. Confirm with `confirmMealAnalysis`
    
    ## Authentication
    All requests require `Authorization: Bearer <token>` header.
  
  version: 2.0.0
  contact:
    name: Nutrifit API Team
    email: api@nutrifit.app
    url: https://nutrifit.app/support
  
  license:
    name: Proprietary
    url: https://nutrifit.app/terms

servers:
  - url: https://api.nutrifit.app/graphql
    description: Production
    production: true
  
  - url: https://staging.nutrifit.app/graphql
    description: Staging
  
  - url: http://localhost:8000/graphql
    description: Local Development

# Example queries (shown in docs)
examples:
  - name: Analyze Meal Photo
    query: |
      mutation AnalyzePhoto {
        analyzeMealPhoto(
          input: {
            userId: "user123"
            photoUrl: "https://storage.nutrifit.app/photos/abc123.jpg"
            dishHint: "carbonara"
            mealType: LUNCH
          }
        ) {
          ... on MealAnalysisSuccess {
            meal {
              id
              dishName
              confidence
              entries {
                label
                displayName
                quantityG
                nutrients {
                  calories
                }
              }
              totalCalories
            }
          }
          ... on MealAnalysisError {
            code
            message
          }
        }
      }
  
  - name: Daily Summary
    query: |
      query DailySummary {
        dailySummary(
          userId: "user123"
          date: "2025-10-22"
        ) {
          ... on DailySummary {
            totalCalories
            totalProtein
            byMealType {
              mealType
              calories
            }
          }
        }
      }
  
  - name: Barcode Scan
    query: |
      mutation ScanBarcode {
        analyzeMealBarcode(
          input: {
            userId: "user123"
            barcode: "8001050000000"
            quantityG: 100
            mealType: SNACK
          }
        ) {
          ... on MealAnalysisSuccess {
            meal {
              id
              entries {
                displayName
                imageUrl
                nutrients {
                  calories
                }
              }
            }
          }
        }
      }

# Extensions to ignore (reduces clutter)
extensions:
  - specifiedByUrl
```

---

### Generate Documentation

```bash
# Export GraphQL schema from code
python backend/scripts/export_schema.py

# Generate SpectaQL docs
npx spectaql spectaql.yaml

# Output: backend/docs/REFACTOR/NEW/api/index.html
```

---

### Export Schema Script

```python
# backend/scripts/export_schema.py
"""
Export GraphQL schema to file

Usage: python backend/scripts/export_schema.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graphql.schema import schema


def export_schema():
    """Export Strawberry schema to SDL file."""
    
    output_path = Path(__file__).parent.parent / "graphql" / "schema.graphql"
    
    # Get SDL from Strawberry schema
    sdl = str(schema)
    
    # Write to file
    output_path.write_text(sdl)
    
    print(f"✅ Schema exported to: {output_path}")
    print(f"   Lines: {len(sdl.splitlines())}")
    print(f"   Size: {len(sdl)} bytes")


if __name__ == "__main__":
    export_schema()
```

---

### Automation (Makefile)

```makefile
# Makefile
.PHONY: docs

# Generate API documentation
docs:
	@echo "📚 Generating API documentation..."
	@python backend/scripts/export_schema.py
	@npx spectaql spectaql.yaml
	@echo "✅ Documentation generated at: backend/docs/REFACTOR/NEW/api/index.html"
	@open backend/docs/REFACTOR/NEW/api/index.html  # macOS only

# Serve docs locally
docs-serve:
	@echo "🌐 Serving documentation at http://localhost:4400"
	@cd backend/docs/REFACTOR/NEW/api && python -m http.server 4400
```

**Usage**:
```bash
# Generate docs
make docs

# Serve locally
make docs-serve
```

---

### CI/CD Integration

```yaml
# .github/workflows/docs.yml
name: Generate API Docs

on:
  push:
    branches: [main, backend2.0]
    paths:
      - 'backend/graphql/**'
      - 'spectaql.yaml'

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          pip install strawberry-graphql
          npm install -g spectaql
      
      - name: Export GraphQL schema
        run: python backend/scripts/export_schema.py
      
      - name: Generate SpectaQL docs
        run: npx spectaql spectaql.yaml
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./backend/docs/REFACTOR/NEW/api
          destination_dir: api-docs
```

**Result**: Docs auto-deployed to `https://yourusername.github.io/nutrifit-mobile/api-docs`

---

## 🎯 Complete Examples

### E2E Workflow: Photo Analysis

```graphql
# Step 1: Upload photo (outside GraphQL)
# POST https://storage.nutrifit.app/upload
# → photoUrl: "https://storage.nutrifit.app/photos/abc123.jpg"

# Step 2: Analyze photo
mutation Step1_AnalyzePhoto {
  analyzeMealPhoto(
    input: {
      userId: "user123"
      photoUrl: "https://storage.nutrifit.app/photos/abc123.jpg"
      dishHint: "carbonara"
      mealType: LUNCH
    }
  ) {
    ... on MealAnalysisSuccess {
      meal {
        id  # → "meal_xyz"
        dishName  # → "Spaghetti alla Carbonara"
        confirmed  # → false
        entries {
          id
          label  # → "pasta, cooked"
          displayName  # → "Pasta cotta"
          quantityG  # → 250
          confidence  # → 0.9
          nutrients {
            calories  # → 350
            protein
            carbs
            fat
          }
        }
        totalCalories  # → 550
      }
      warnings  # → []
    }
    ... on MealAnalysisError {
      code
      message
    }
  }
}

# Step 3: User reviews and confirms
mutation Step2_ConfirmMeal {
  confirmMealAnalysis(
    input: {
      mealId: "meal_xyz"
      userId: "user123"
      confirmedEntryIds: ["entry_1", "entry_2"]  # Keep pasta + eggs
    }
  ) {
    ... on ConfirmationSuccess {
      meal {
        id
        confirmed  # → true
        confirmedAt  # → "2025-10-22T10:30:00Z"
        entries {
          id
          displayName
        }
      }
    }
  }
}

# Step 4: View daily summary
query Step3_DailySummary {
  dailySummary(
    userId: "user123"
    date: "2025-10-22"
  ) {
    ... on DailySummary {
      totalCalories
      byMealType {
        mealType
        calories
      }
      meals {
        dishName
        totalCalories
      }
    }
  }
}
```

---

## 📊 Performance Considerations

### Query Complexity

```python
# graphql/complexity.py
"""
Query complexity limits (prevent abuse)
"""

from strawberry.extensions import QueryDepthLimiter, MaxTokensLimiter

extensions = [
    QueryDepthLimiter(max_depth=10),        # Max nesting
    MaxTokensLimiter(max_token_count=1000),  # Max query size
]
```

### DataLoader (N+1 Prevention)

```python
# graphql/dataloaders.py
"""
DataLoader for batch loading

Prevents N+1 queries when loading nutrients for multiple entries.
"""

from strawberry.dataloader import DataLoader
from typing import List


async def load_nutrients_batch(entry_ids: List[str]) -> List[NutrientProfile]:
    """Batch load nutrients for entries."""
    # Fetch all in single query
    return await nutrient_repository.get_by_entry_ids(entry_ids)


nutrient_loader = DataLoader(load_fn=load_nutrients_batch)
```

---

## 🎉 Summary

### Key Achievements

1. ✅ **Complete Schema**: 6 mutations + 7 queries
2. ✅ **Type Safety**: Union types for errors
3. ✅ **Documentation**: SpectaQL auto-generation
4. ✅ **Examples**: Real-world workflows
5. ✅ **Mapping**: GraphQL ↔ Application layer
6. ✅ **Performance**: Complexity limits + DataLoader
7. ✅ **CI/CD**: Auto-deploy docs on schema changes

### GraphQL Operations Summary

**Mutations**:
- `analyzeMealPhoto` → Photo recognition workflow
- `analyzeMealBarcode` → Barcode scan workflow
- `analyzeMealDescription` → Text extraction workflow
- `confirmMealAnalysis` → 2-step confirmation
- `updateMeal` → Edit existing meal
- `deleteMeal` → Soft delete

**Queries**:
- `meal` → Get single meal
- `mealHistory` → List with filters
- `searchMeals` → Text search
- `dailySummary` → Daily aggregation
- `recognizeFood` → Atomic utility (OpenAI)
- `enrichNutrients` → Atomic utility (USDA)
- `searchFoodByBarcode` → Atomic utility (OpenFoodFacts)

**Next**: `README.md` - Navigation index

**Last Updated**: 22 Ottobre 2025
