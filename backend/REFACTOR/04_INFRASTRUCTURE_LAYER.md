# 🏗️ Infrastructure Layer - Implementation Details

**Data:** 22 Ottobre 2025  
**Layer:** Infrastructure (External Dependencies & Adapters)  
**Dependencies:** Domain Ports (interfaces only)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [OpenAI Integration](#openai-integration)
3. [USDA Integration](#usda-integration)
4. [OpenFoodFacts Integration](#openfoodfacts-integration)
5. [Repositories](#repositories)
6. [Event Bus](#event-bus)
7. [Circuit Breaker Pattern](#circuit-breaker-pattern)

---

## 🎯 Overview

L'Infrastructure Layer implementa **adapters** che forniscono le dipendenze richieste dal Domain tramite **Ports** (interfaces).

### Principles
- ✅ **Implements Domain Ports**: Infrastructure → Domain (Dependency Inversion)
- ✅ **External Dependencies**: API clients, databases, message queues
- ✅ **Resilience**: Circuit breakers, retries, timeouts
- ✅ **Testability**: Easy to mock/stub for testing
- ✅ **Configuration**: Environment-based settings

### GraphQL Operations Mapping

Questo layer supporta le seguenti operazioni GraphQL:

**Mutations**:
- `analyzeMealPhoto` → OpenAI + USDA
- `analyzeMealBarcode` → OpenFoodFacts + USDA
- `analyzeMealDescription` → OpenAI + USDA
- `confirmMealAnalysis` → Repository

**Queries**:
- `recognizeFood` → OpenAI (utility atomica)
- `enrichNutrients` → USDA (utility atomica)
- `searchFoodByBarcode` → OpenFoodFacts (utility atomica)

---

## 🤖 OpenAI Integration

### Context: GraphQL Operations
- **`analyzeMealPhoto`**: Usa OpenAI Vision per riconoscere alimenti da foto
- **`analyzeMealDescription`**: Usa OpenAI per estrarre alimenti da testo
- **`recognizeFood`**: Query atomica per testing/debugging

### Why OpenAI v2.5.0?
- ✅ **Structured Outputs**: Native Pydantic support (no JSON parsing)
- ✅ **Prompt Caching**: System prompt >1024 token → 50% cost reduction
- ✅ **Reliability**: Strict schema validation by OpenAI

---

### 1. Installation

```toml
# pyproject.toml
[project.dependencies]
openai = "^2.5.0"
pydantic = "^2.0"
circuitbreaker = "^1.4.0"
tenacity = "^8.2.0"
```

---

### 2. OpenAI Client with Structured Outputs

```python
# infrastructure/ai/openai_client.py
"""
OpenAI Client v2.5.0 - Implements IVisionProvider

Key Features:
- Structured outputs (native Pydantic)
- Prompt caching (>1024 token system prompt)
- Circuit breaker (5 failures → 60s timeout)
- Retry logic (exponential backoff)
- Cache metrics tracking

GraphQL Operations: analyzeMealPhoto, analyzeMealDescription, recognizeFood
"""

import logging
from typing import List, Dict, Type, TypeVar, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from circuitbreaker import circuit
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OpenAIClient:
    """OpenAI API client with v2.5.0 structured outputs."""
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o-mini-2024-07-18"
        self._cache_stats = {"hits": 0, "misses": 0}
    
    @circuit(failure_threshold=5, recovery_timeout=60, name="openai")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def structured_complete(
        self,
        messages: List[Dict],
        response_model: Type[T],
        system_prompt: str = None,
        temperature: float = 0.1,
    ) -> T:
        """
        Execute OpenAI completion with structured output.
        
        Args:
            messages: User messages (with images if Vision)
            response_model: Pydantic model for response
            system_prompt: System prompt (should be >1024 tokens for caching)
            temperature: Sampling temperature (0.1 for consistency)
            
        Returns:
            Parsed Pydantic model instance
            
        Raises:
            openai.APIError: On API failures
            ValidationError: On schema validation failures
        """
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        logger.info(
            "openai_request",
            model=self.model,
            response_model=response_model.__name__,
            message_count=len(messages)
        )
        
        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=response_model,  # Native Pydantic!
            temperature=temperature,
        )
        
        # Track cache metrics
        usage = response.usage
        if hasattr(usage, "prompt_tokens_details"):
            cached = getattr(usage.prompt_tokens_details, "cached_tokens", 0)
            if cached > 0:
                self._cache_stats["hits"] += 1
                logger.info("openai_cache_hit", cached_tokens=cached)
            else:
                self._cache_stats["misses"] += 1
        
        result = response.choices[0].message.parsed
        
        logger.info(
            "openai_response",
            model=self.model,
            total_tokens=usage.total_tokens,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens
        )
        
        return result
    
    def get_cache_stats(self) -> dict:
        """Get cache performance stats."""
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total * 100) if total > 0 else 0
        return {
            **self._cache_stats,
            "hit_rate_percent": round(hit_rate, 2)
        }
```

---

### 3. System Prompt (>1024 tokens) - CRITICAL

**⚠️ IMPORTANTE**: Il system prompt DEVE essere >1024 token per attivare il caching di OpenAI.

**🎯 OBIETTIVO CHIAVE**: Generare JSON con **label USDA-compatibili** per ridurre ambiguità nelle ricerche USDA.

```python
# infrastructure/ai/prompts/food_recognition.py
"""
System Prompt for Food Recognition (>1024 tokens)

CRITICAL REQUIREMENTS:
1. Label must be USDA-compatible (English, specific)
2. Disambiguate when necessary:
   - "chicken, roasted" vs "chicken, fried"
   - "potato, boiled" vs "potato, french fried"
   - "egg white" vs "egg, whole"
3. Plural forms for USDA: "eggs", "potatoes", "carrots"
4. Display names in Italian for UX

Why this matters:
- USDA search returns MULTIPLE results for vague labels
- "chicken" → 500+ results
- "chicken breast, roasted" → 5-10 results (precise match)
"""

FOOD_RECOGNITION_SYSTEM_PROMPT = """
You are an expert nutritionist specialized in visual food analysis for the USDA FoodData Central database.

=== PRIMARY OBJECTIVE ===
Your goal is to generate PRECISE, UNAMBIGUOUS food labels that will be used to search the USDA database.
VAGUE labels cause multiple search results and confusion. SPECIFIC labels get exact matches.

=== CRITICAL LABEL RULES ===

Rule 1: ALWAYS include cooking method
- ❌ BAD: "chicken"
- ✅ GOOD: "chicken breast, roasted"
- ❌ BAD: "potato"
- ✅ GOOD: "potato, boiled"

Rule 2: Specify preparation when ambiguous
- Eggs: "egg, whole" vs "egg white" vs "egg yolk"
- Meat cuts: "beef, ground" vs "beef, steak, sirloin"
- Fish: "salmon, raw" vs "salmon, cooked, dry heat"

Rule 3: Use USDA plural forms
- "eggs" (not "egg")
- "potatoes" (not "potato") 
- "carrots" (not "carrot")
- "tomatoes" (not "tomato")

Rule 4: Cooking state matters
- "pasta, cooked" vs "pasta, dry"
- "rice, white, cooked" vs "rice, white, raw"
- "beans, black, cooked" vs "beans, black, raw"

=== LABEL EXAMPLES (USDA-compatible) ===

Italian Dishes:
- "Carbonara" → "pasta, cooked" + "eggs" + "pork, bacon"
- "Pizza Margherita" → "pizza, cheese" + "tomato sauce"
- "Risotto" → "rice, white, cooked" + "butter" + "cheese, parmesan"

Common Foods:
- "Insalata" → "lettuce, green" + "tomatoes, raw" + "cucumber"
- "Pollo alla griglia" → "chicken breast, grilled"
- "Patate fritte" → "potato, french fried"
- "Uova sode" → "egg, whole, boiled"

Beverages:
- "Latte" → "milk, whole"
- "Caffè" → "coffee, brewed"
- "Succo d'arancia" → "orange juice, raw"

=== METHODOLOGY ===

Step 1: Dish Identification
- Analyze complete dish composition
- Recognize preparation method from visual cues:
  - Golden/crispy = fried
  - Grill marks = grilled
  - Boiled appearance = boiled
  - Brown/caramelized = roasted

Step 2: Ingredient Breakdown
- Maximum 5 main ingredients (nutritionally significant)
- Order by visual prominence
- ALWAYS specify cooking method

Step 3: Quantity Estimation
Reference sizes:
- Normal plate: 23-25cm diameter
- Pasta portion: 80-120g raw → 200-300g cooked
- Meat portion: 150-250g
- Vegetables: 100-200g
- Use CONSERVATIVE estimates when uncertain

Step 4: Confidence Scoring
- 0.9-1.0: Food clearly visible, cooking method evident
- 0.7-0.8: Food recognizable, cooking method assumed
- 0.5-0.6: Food partially visible/hidden
- <0.5: Too uncertain (DISCARD)

=== AMBIGUITY RESOLUTION ===

When uncertain about cooking method:
1. Look for visual cues (color, texture, moisture)
2. Consider dish context (e.g., carbonara → cooked pasta)
3. Default to most common preparation
4. Reflect uncertainty in confidence score (0.6-0.7)

Examples:
- Chicken appearance unclear → "chicken breast, cooked"
- Potatoes (not fried) → "potato, boiled"
- Pasta in sauce → "pasta, cooked"

=== OUTPUT FORMAT ===

Return Pydantic model with:

1. dish_title: str
   - Italian name of complete dish
   - Example: "Spaghetti alla Carbonara"

2. items: List[RecognizedFood]
   Each item MUST have:
   - label: str (USDA-compatible, English, specific)
   - display_name: str (Italian, user-friendly)
   - quantity: Quantity (value + unit)
   - confidence: float (0.0-1.0)

=== COMPLETE EXAMPLES ===

Example 1: Carbonara
Input: Photo of spaghetti carbonara
Output: {
  "dish_title": "Spaghetti alla Carbonara",
  "items": [
    {
      "label": "pasta, cooked",
      "display_name": "Pasta cotta",
      "quantity": {"value": 250, "unit": "g"},
      "confidence": 0.9
    },
    {
      "label": "eggs",
      "display_name": "Uova",
      "quantity": {"value": 50, "unit": "g"},
      "confidence": 0.8
    },
    {
      "label": "pork, bacon, cooked",
      "display_name": "Pancetta",
      "quantity": {"value": 30, "unit": "g"},
      "confidence": 0.85
    },
    {
      "label": "cheese, parmesan, grated",
      "display_name": "Parmigiano grattugiato",
      "quantity": {"value": 20, "unit": "g"},
      "confidence": 0.9
    }
  ]
}

Example 2: Grilled Chicken with Salad
Input: Photo of grilled chicken breast with mixed salad
Output: {
  "dish_title": "Petto di Pollo alla Griglia con Insalata",
  "items": [
    {
      "label": "chicken breast, grilled",
      "display_name": "Petto di pollo alla griglia",
      "quantity": {"value": 200, "unit": "g"},
      "confidence": 0.95
    },
    {
      "label": "lettuce, green",
      "display_name": "Lattuga",
      "quantity": {"value": 80, "unit": "g"},
      "confidence": 0.9
    },
    {
      "label": "tomatoes, raw",
      "display_name": "Pomodori crudi",
      "quantity": {"value": 50, "unit": "g"},
      "confidence": 0.85
    }
  ]
}

Example 3: Margherita Pizza
Input: Photo of pizza margherita
Output: {
  "dish_title": "Pizza Margherita",
  "items": [
    {
      "label": "pizza, cheese",
      "display_name": "Pizza al formaggio",
      "quantity": {"value": 300, "unit": "g"},
      "confidence": 0.95
    }
  ]
}

=== QUALITY OVER QUANTITY ===
- Better to return 2-3 precise items than 5 vague ones
- If confidence < 0.6, EXCLUDE the item
- Precision is CRITICAL for USDA matching

=== REMEMBER ===
Your labels will be used DIRECTLY to query USDA FoodData Central.
Vague labels = multiple results = user confusion.
Specific labels = exact matches = happy users.

ALWAYS ask yourself: "Will this label find a SINGLE, CLEAR match in USDA?"
"""

# Verify token count (must be >1024 for caching)
def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 chars)."""
    return len(text) // 4

_token_count = estimate_tokens(FOOD_RECOGNITION_SYSTEM_PROMPT)
assert _token_count >= 1024, f"System prompt too short: {_token_count} tokens (need ≥1024)"

print(f"✅ System prompt ready: {_token_count} tokens (caching enabled)")
```

---

### 4. Pydantic Models

```python
# domain/meal/recognition/entities/recognized_food.py
from pydantic import BaseModel, Field
from typing import List


class Quantity(BaseModel):
    """Quantity with unit."""
    value: float = Field(gt=0, le=5000, description="Quantity value")
    unit: str = Field(pattern="^(g|ml|piece)$", description="Unit (g, ml, piece)")


class RecognizedFood(BaseModel):
    """Single recognized food item."""
    label: str = Field(
        min_length=2,
        max_length=100,
        description="USDA-compatible label (English, specific)"
    )
    display_name: str = Field(
        min_length=2,
        max_length=100,
        description="User-friendly name (Italian)"
    )
    quantity: Quantity = Field(description="Estimated quantity")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)"
    )


class RecognitionResult(BaseModel):
    """Complete recognition result."""
    dish_title: str = Field(
        max_length=200,
        description="Complete dish name (Italian)"
    )
    items: List[RecognizedFood] = Field(
        min_length=1,
        max_length=5,
        description="Recognized food items"
    )
```

---

### 5. Vision Provider Implementation

```python
# infrastructure/ai/vision_provider.py
"""
OpenAI Vision Provider - Implements IVisionProvider port

GraphQL Operations: analyzeMealPhoto, analyzeMealDescription, recognizeFood
"""

from typing import Optional
import structlog

from domain.meal.recognition.ports.vision_provider import IVisionProvider
from domain.meal.recognition.entities.recognized_food import FoodRecognitionResult
from .openai_client import OpenAIClient
from .prompts.food_recognition import FOOD_RECOGNITION_SYSTEM_PROMPT

logger = structlog.get_logger(__name__)


class OpenAIVisionProvider:
    """OpenAI implementation of IVisionProvider."""
    
    def __init__(self, client: OpenAIClient):
        self._client = client
    
    async def analyze_photo(
        self,
        photo_url: str,
        hint: Optional[str] = None
    ) -> FoodRecognitionResult:
        """
        Analyze photo and recognize food items.
        
        Used by: analyzeMealPhoto mutation
        
        Args:
            photo_url: URL of meal photo (will be saved in MealEntry.image_url)
            hint: Optional user hint (e.g., "carbonara")
            
        Returns:
            FoodRecognitionResult with USDA-compatible labels
        """
        logger.info(
            "analyzing_photo",
            photo_url=photo_url,
            has_hint=hint is not None
        )
        
        # Build user message with image
        user_content = []
        
        if hint:
            user_content.append({
                "type": "text",
                "text": f"User hint: {hint}\n\nAnalyze this meal photo:"
            })
        else:
            user_content.append({
                "type": "text",
                "text": "Analyze this meal photo:"
            })
        
        user_content.append({
            "type": "image_url",
            "image_url": {"url": photo_url}
        })
        
        user_message = {
            "role": "user",
            "content": user_content
        }
        
        # Call OpenAI with structured output
        result = await self._client.structured_complete(
            messages=[user_message],
            response_model=RecognitionResult,
            system_prompt=FOOD_RECOGNITION_SYSTEM_PROMPT,
            temperature=0.1
        )
        
        logger.info(
            "photo_analyzed",
            dish_title=result.dish_title,
            item_count=len(result.items),
            avg_confidence=sum(i.confidence for i in result.items) / len(result.items)
        )
        
        # Convert Pydantic → Domain entity
        return FoodRecognitionResult(
            items=[
                RecognizedFood(
                    label=item.label,
                    display_name=item.display_name,
                    quantity_g=item.quantity.value,
                    confidence=item.confidence,
                    category=None  # TODO: Infer from label
                )
                for item in result.items
            ],
            dish_name=result.dish_title,
            confidence=sum(i.confidence for i in result.items) / len(result.items),
            processing_time_ms=0  # TODO: Track time
        )
    
    async def analyze_text(
        self,
        description: str
    ) -> FoodRecognitionResult:
        """
        Extract food items from text description.
        
        Used by: analyzeMealDescription mutation
        
        Args:
            description: Text description (e.g., "pasta al pomodoro e insalata")
            
        Returns:
            FoodRecognitionResult with USDA-compatible labels
        """
        logger.info("analyzing_text", text_length=len(description))
        
        user_message = {
            "role": "user",
            "content": f"Extract food items from this description:\n\n{description}"
        }
        
        result = await self._client.structured_complete(
            messages=[user_message],
            response_model=RecognitionResult,
            system_prompt=FOOD_RECOGNITION_SYSTEM_PROMPT,
            temperature=0.1
        )
        
        logger.info(
            "text_analyzed",
            dish_title=result.dish_title,
            item_count=len(result.items)
        )
        
        # Convert Pydantic → Domain entity
        return FoodRecognitionResult(
            items=[
                RecognizedFood(
                    label=item.label,
                    display_name=item.display_name,
                    quantity_g=item.quantity.value,
                    confidence=item.confidence,
                    category=None
                )
                for item in result.items
            ],
            dish_name=result.dish_title,
            confidence=sum(i.confidence for i in result.items) / len(result.items),
            processing_time_ms=0
        )
```

---

## 🥗 USDA Integration

### Context: GraphQL Operations
- **`analyzeMealPhoto`**: Arricchisce alimenti riconosciuti con dati USDA
- **`analyzeMealBarcode`**: Fallback a USDA se barcode non ha nutrienti
- **`analyzeMealDescription`**: Arricchisce alimenti estratti da testo
- **`enrichNutrients`**: Query atomica per arricchimento singolo

### Why USDA Precision Matters

**Problema**: Query vaghe restituiscono TROPPI risultati.

Esempio:
```
Query: "chicken"
Results: 500+ items
- Chicken, broilers or fryers, breast, meat only, cooked, roasted
- Chicken, broilers or fryers, breast, meat only, raw
- Chicken, broilers or fryers, breast, meat and skin, cooked, fried
- ... (497 more)
```

**Soluzione**: OpenAI genera label SPECIFICHE.

Esempio:
```
Query: "chicken breast, roasted"
Results: 5-10 items (exact match molto più probabile)
```

---

### 1. USDA Client (Mantieni logica esistente + Circuit Breaker)

```python
# infrastructure/external_apis/usda/client.py
"""
USDA FoodData Central API Client

GraphQL Operations: analyzeMealPhoto, analyzeMealBarcode, analyzeMealDescription, enrichNutrients
"""

from typing import List, Dict, Optional
import httpx
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger(__name__)


class USDAClient:
    """USDA FoodData Central API client with resilience."""
    
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session: Optional[httpx.AsyncClient] = None
    
    def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = httpx.AsyncClient(timeout=10.0)
        return self._session
    
    @circuit(failure_threshold=5, recovery_timeout=60, name="usda")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search_food(
        self,
        query: str,
        page_size: int = 5,
        data_types: List[str] = None
    ) -> List[Dict]:
        """
        Search USDA foods.
        
        Args:
            query: USDA-compatible label (e.g., "chicken breast, roasted")
            page_size: Max results (default: 5)
            data_types: Filter by data type (default: ["Foundation", "SR Legacy"])
            
        Returns:
            List of food items with fdcId, description, dataType
            
        Raises:
            httpx.HTTPError: On API failures
        """
        if data_types is None:
            data_types = ["Foundation", "SR Legacy"]
        
        logger.info("usda_search", query=query, page_size=page_size)
        
        params = {
            "query": query,
            "pageSize": page_size,
            "api_key": self.api_key,
            "dataType": data_types
        }
        
        try:
            response = await self._get_session().get(
                f"{self.BASE_URL}/foods/search",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            foods = data.get("foods", [])
            
            logger.info(
                "usda_search_success",
                query=query,
                result_count=len(foods)
            )
            
            return foods
            
        except httpx.HTTPError as e:
            logger.error("usda_search_failed", query=query, error=str(e))
            raise
    
    @circuit(failure_threshold=5, recovery_timeout=60, name="usda")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_nutrients(
        self,
        fdc_id: int
    ) -> Dict:
        """
        Get food nutrients by FDC ID.
        
        Args:
            fdc_id: USDA FoodData Central ID
            
        Returns:
            Food details with nutrients
            
        Raises:
            httpx.HTTPError: On API failures
        """
        logger.info("usda_get_nutrients", fdc_id=fdc_id)
        
        try:
            response = await self._get_session().get(
                f"{self.BASE_URL}/food/{fdc_id}",
                params={"api_key": self.api_key}
            )
            response.raise_for_status()
            
            data = response.json()
            
            logger.info("usda_get_nutrients_success", fdc_id=fdc_id)
            
            return data
            
        except httpx.HTTPError as e:
            logger.error("usda_get_nutrients_failed", fdc_id=fdc_id, error=str(e))
            raise
    
    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None
```

---

### 2. USDA Mapper

```python
# infrastructure/external_apis/usda/mapper.py
"""
USDA Response → NutrientProfile mapper

Maps USDA API responses to domain NutrientProfile entities.
"""

from typing import Dict, Any, Optional
import structlog

from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile

logger = structlog.get_logger(__name__)

# USDA nutrient IDs (constant)
NUTRIENT_IDS = {
    "calories": 1008,     # Energy (kcal)
    "protein": 1003,      # Protein (g)
    "carbs": 1005,        # Carbohydrates (g)
    "fat": 1004,          # Total lipid (fat) (g)
    "fiber": 1079,        # Fiber, total dietary (g)
    "sugar": 2000,        # Sugars, total (g)
    "sodium": 1093,       # Sodium (mg)
}


class USDAMapper:
    """Map USDA API responses to NutrientProfile."""
    
    @staticmethod
    def map_food_to_profile(usda_food: Dict[str, Any]) -> Optional[NutrientProfile]:
        """
        Map USDA food response to NutrientProfile.
        
        Args:
            usda_food: USDA API response with foodNutrients array
            
        Returns:
            NutrientProfile or None if mapping fails
        """
        try:
            # Extract nutrients by ID
            nutrients_map = {}
            for nutrient in usda_food.get("foodNutrients", []):
                nutrient_id = nutrient.get("nutrient", {}).get("id")
                amount = nutrient.get("amount", 0)
                
                for name, nid in NUTRIENT_IDS.items():
                    if nutrient_id == nid:
                        nutrients_map[name] = amount
                        break
            
            # Validate required fields
            if "calories" not in nutrients_map:
                logger.warning("usda_no_calories", fdc_id=usda_food.get("fdcId"))
                return None
            
            profile = NutrientProfile(
                calories=int(nutrients_map.get("calories", 0)),
                protein=float(nutrients_map.get("protein", 0)),
                carbs=float(nutrients_map.get("carbs", 0)),
                fat=float(nutrients_map.get("fat", 0)),
                fiber=float(nutrients_map.get("fiber")) if "fiber" in nutrients_map else None,
                sugar=float(nutrients_map.get("sugar")) if "sugar" in nutrients_map else None,
                sodium=float(nutrients_map.get("sodium")) if "sodium" in nutrients_map else None,
                source="USDA",
                confidence=0.9,  # USDA = high quality
                quantity_g=100.0  # USDA reference is per 100g
            )
            
            logger.info(
                "usda_mapped",
                fdc_id=usda_food.get("fdcId"),
                calories=profile.calories
            )
            
            return profile
            
        except Exception as e:
            logger.error("usda_mapping_failed", error=str(e))
            return None
```

---

### 3. USDA Provider Implementation

```python
# infrastructure/external_apis/usda/provider.py
"""
USDA Nutrition Provider - Implements INutritionProvider port

GraphQL Operations: analyzeMealPhoto, analyzeMealBarcode, analyzeMealDescription, enrichNutrients
"""

from typing import Optional
import structlog

from domain.meal.nutrition.ports.nutrition_provider import INutritionProvider
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile
from .client import USDAClient
from .mapper import USDAMapper

logger = structlog.get_logger(__name__)


class USDANutritionProvider:
    """USDA implementation of INutritionProvider."""
    
    def __init__(self, client: USDAClient, mapper: USDAMapper):
        self._client = client
        self._mapper = mapper
    
    async def get_nutrients(
        self,
        identifier: str,
        quantity_g: float
    ) -> Optional[NutrientProfile]:
        """
        Get nutrients from USDA.
        
        Args:
            identifier: USDA-compatible label (e.g., "chicken breast, roasted")
            quantity_g: Quantity (will be scaled from 100g reference)
            
        Returns:
            NutrientProfile scaled to quantity or None if not found
        """
        logger.info("usda_get_nutrients", identifier=identifier, quantity_g=quantity_g)
        
        # Search USDA
        foods = await self._client.search_food(identifier, page_size=5)
        
        if not foods:
            logger.warning("usda_no_results", identifier=identifier)
            return None
        
        # Take first result (best match)
        first_food = foods[0]
        fdc_id = first_food.get("fdcId")
        
        # Get detailed nutrients
        food_details = await self._client.get_nutrients(fdc_id)
        
        # Map to domain
        profile = self._mapper.map_food_to_profile(food_details)
        
        if not profile:
            return None
        
        # Scale to target quantity
        return profile.scale_to_quantity(quantity_g)
```

---

## 🏷️ OpenFoodFacts Integration

### Context: GraphQL Operations
- **`analyzeMealBarcode`**: Lookup prodotto da barcode
- **`searchFoodByBarcode`**: Query atomica per barcode lookup

### ⚠️ CRITICAL: Image URL Handling

**IMPORTANTE**: Il client OpenFoodFacts DEVE SEMPRE richiedere e salvare l'image_url del prodotto.

**Perché?**
- L'utente scansiona un barcode → vuole vedere la foto del prodotto
- La foto viene salvata in `MealEntry.image_url`
- Sarà mostrata nella UI insieme ai dati nutrizionali

---

### 1. OpenFoodFacts Client

```python
# infrastructure/external_apis/openfoodfacts/client.py
"""
OpenFoodFacts API Client

GraphQL Operations: analyzeMealBarcode, searchFoodByBarcode
"""

from typing import Optional, Dict
import httpx
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger(__name__)


class OpenFoodFactsClient:
    """OpenFoodFacts API client with resilience."""
    
    BASE_URL = "https://world.openfoodfacts.org/api/v2"
    SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
    
    def __init__(self):
        self._session: Optional[httpx.AsyncClient] = None
    
    def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = httpx.AsyncClient(timeout=10.0)
        return self._session
    
    @circuit(failure_threshold=5, recovery_timeout=60, name="openfoodfacts")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_product(
        self,
        barcode: str
    ) -> Optional[Dict]:
        """
        Get product by barcode.
        
        ⚠️ IMPORTANT: Always includes image_url in response
        
        Args:
            barcode: Product barcode (EAN/UPC)
            
        Returns:
            Product dict with:
            - code: str (barcode)
            - product_name: str
            - brands: str (optional)
            - image_url: str (⚠️ CRITICAL - for MealEntry.image_url)
            - nutriments: dict (calories, proteins, carbohydrates, fat, etc.)
            
            Returns None if product not found
        """
        logger.info("openfoodfacts_lookup", barcode=barcode)
        
        try:
            response = await self._get_session().get(
                f"{self.BASE_URL}/product/{barcode}.json"
            )
            
            data = response.json()
            
            if data.get("status") != 1:
                logger.warning("openfoodfacts_not_found", barcode=barcode)
                return None
            
            product = data.get("product", {})
            
            # ⚠️ CRITICAL: Extract image URL
            image_url = (
                product.get("image_url") or
                product.get("image_front_url") or
                product.get("image_front_small_url")
            )
            
            if not image_url:
                logger.warning("openfoodfacts_no_image", barcode=barcode)
            
            logger.info(
                "openfoodfacts_success",
                barcode=barcode,
                name=product.get("product_name"),
                has_image=bool(image_url)
            )
            
            # Return product with image_url
            return {
                "code": barcode,
                "product_name": product.get("product_name"),
                "brands": product.get("brands"),
                "image_url": image_url,  # ⚠️ CRITICAL
                "nutriments": product.get("nutriments", {}),
                "categories": product.get("categories"),
            }
            
        except httpx.HTTPError as e:
            logger.error("openfoodfacts_failed", barcode=barcode, error=str(e))
            raise
    
    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None
```

---

### 2. OpenFoodFacts Provider

```python
# infrastructure/external_apis/openfoodfacts/provider.py
"""
OpenFoodFacts Barcode Provider - Implements IBarcodeProvider port

GraphQL Operations: analyzeMealBarcode, searchFoodByBarcode
"""

from typing import Optional, Dict
import structlog

from domain.meal.barcode.ports.barcode_provider import IBarcodeProvider
from .client import OpenFoodFactsClient

logger = structlog.get_logger(__name__)


class OpenFoodFactsBarcodeProvider:
    """OpenFoodFacts implementation of IBarcodeProvider."""
    
    def __init__(self, client: OpenFoodFactsClient):
        self._client = client
    
    async def lookup_product(
        self,
        barcode: str
    ) -> Optional[Dict]:
        """
        Lookup product by barcode.
        
        Returns:
            Product dict with:
            - name: str
            - barcode: str
            - image_url: str (⚠️ CRITICAL - will be saved in MealEntry)
            - nutrients: dict (optional, may be None)
            - category: str (optional)
            
            Returns None if not found
        """
        logger.info("looking_up_barcode", barcode=barcode)
        
        product = await self._client.get_product(barcode)
        
        if not product:
            return None
        
        # Map to domain format
        return {
            "name": product["product_name"],
            "barcode": product["code"],
            "image_url": product["image_url"],  # ⚠️ CRITICAL
            "brand": product.get("brands"),
            "category": product.get("categories"),
            "nutrients": self._extract_nutrients(product["nutriments"])
                if product.get("nutriments") else None
        }
    
    def _extract_nutrients(self, nutriments: Dict) -> Dict:
        """Extract nutrients from OpenFoodFacts nutriments."""
        # Per 100g (OpenFoodFacts standard)
        return {
            "calories": int(nutriments.get("energy-kcal_100g", 0)),
            "protein": float(nutriments.get("proteins_100g", 0)),
            "carbs": float(nutriments.get("carbohydrates_100g", 0)),
            "fat": float(nutriments.get("fat_100g", 0)),
            "fiber": float(nutriments.get("fiber_100g")) if "fiber_100g" in nutriments else None,
            "sugar": float(nutriments.get("sugars_100g")) if "sugars_100g" in nutriments else None,
            "sodium": float(nutriments.get("sodium_100g")) if "sodium_100g" in nutriments else None,
        }
```

---

## 💾 Repositories

### In-Memory Repository (Development/Testing)

```python
# infrastructure/persistence/in_memory/meal_repository.py
"""
In-Memory Meal Repository - Implements IMealRepository

Used for: Development, Testing

GraphQL Operations: ALL (save/retrieve meals)
"""

from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
import structlog

from domain.meal.core.entities.meal import Meal
from domain.shared.ports.repository import IMealRepository

logger = structlog.get_logger(__name__)


class InMemoryMealRepository:
    """In-memory implementation of IMealRepository."""
    
    def __init__(self):
        self._storage: Dict[UUID, Meal] = {}
    
    async def save(self, meal: Meal) -> None:
        """Persist meal in memory."""
        self._storage[meal.id] = meal
        logger.info("meal_saved", meal_id=str(meal.id), storage_size=len(self._storage))
    
    async def get_by_id(self, meal_id: UUID) -> Optional[Meal]:
        """Get meal by ID."""
        meal = self._storage.get(meal_id)
        logger.info("meal_retrieved", meal_id=str(meal_id), found=meal is not None)
        return meal
    
    async def list_by_user(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Meal]:
        """List meals for user with filters."""
        meals = [
            m for m in self._storage.values()
            if m.user_id == user_id
        ]
        
        # Apply date filters
        if start_date:
            meals = [m for m in meals if m.timestamp >= start_date]
        if end_date:
            meals = [m for m in meals if m.timestamp <= end_date]
        
        # Sort by timestamp (newest first)
        meals.sort(key=lambda m: m.timestamp, reverse=True)
        
        # Apply pagination
        result = meals[offset:offset + limit]
        
        logger.info(
            "meals_listed",
            user_id=user_id,
            total_count=len(meals),
            returned_count=len(result)
        )
        
        return result
    
    async def delete(self, meal_id: UUID) -> bool:
        """Delete meal."""
        if meal_id in self._storage:
            del self._storage[meal_id]
            logger.info("meal_deleted", meal_id=str(meal_id))
            return True
        
        logger.warning("meal_not_found_for_deletion", meal_id=str(meal_id))
        return False
    
    async def exists(self, meal_id: UUID) -> bool:
        """Check if meal exists."""
        return meal_id in self._storage
    
    def clear(self) -> None:
        """Clear all meals (testing utility)."""
        self._storage.clear()
        logger.info("storage_cleared")
```

---

## 🔄 Circuit Breaker Pattern

### Why Circuit Breakers?

**Problem**: External APIs fail → cascading failures → system down

**Solution**: Circuit breaker stops calling failing services temporarily.

**States**:
1. **CLOSED**: Normal operation, calls go through
2. **OPEN**: Failures exceeded threshold, calls blocked
3. **HALF_OPEN**: Testing if service recovered

---

### Configuration

```python
# infrastructure/config/circuit_breaker_config.py
"""
Circuit Breaker Configuration

All external API clients (OpenAI, USDA, OpenFoodFacts) use circuit breakers.
"""

from circuitbreaker import CircuitBreakerMonitor
from dataclasses import dataclass
from typing import Dict


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker settings."""
    failure_threshold: int = 5      # Open after 5 failures
    recovery_timeout: int = 60      # Try recovery after 60s
    expected_exception: type = Exception


# Service-specific configs
OPENAI_CB_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60
)

USDA_CB_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60
)

OPENFOODFACTS_CB_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60
)


def get_circuit_breaker_status() -> Dict:
    """
    Get status of all circuit breakers.
    
    Returns:
        Dict mapping circuit name → status
    """
    status = {}
    
    for cb in CircuitBreakerMonitor.get_circuits():
        status[cb.name] = {
            "state": cb.current_state,
            "failure_count": cb.failure_count,
            "last_failure": cb.last_failure_time,
        }
    
    return status
```

---

## 📊 Testing Infrastructure

### Example: Testing OpenAI Provider with Dependency Injection

```python
# tests/unit/infrastructure/ai/test_vision_provider.py
"""
Unit tests for OpenAIVisionProvider

Key principles:
- Use dependency injection (mock OpenAIClient, not HTTP)
- Test behavior, not implementation
- No stubs unless necessary (prefer real Pydantic models)
"""

import pytest
from unittest.mock import AsyncMock, Mock

from infrastructure.ai.vision_provider import OpenAIVisionProvider
from domain.meal.recognition.entities.recognized_food import RecognitionResult, RecognizedFood, Quantity


@pytest.fixture
def mock_openai_client():
    """Mock OpenAIClient (injected dependency)."""
    return AsyncMock()


@pytest.fixture
def vision_provider(mock_openai_client):
    """Create OpenAIVisionProvider with mocked client."""
    return OpenAIVisionProvider(client=mock_openai_client)


@pytest.mark.asyncio
async def test_analyze_photo_returns_usda_compatible_labels(vision_provider, mock_openai_client):
    """Test that analyze_photo returns USDA-compatible labels."""
    # Arrange
    mock_response = RecognitionResult(
        dish_title="Spaghetti alla Carbonara",
        items=[
            RecognizedFood(
                label="pasta, cooked",  # ✅ USDA-compatible
                display_name="Pasta cotta",
                quantity=Quantity(value=250, unit="g"),
                confidence=0.9
            ),
            RecognizedFood(
                label="eggs",  # ✅ USDA plural form
                display_name="Uova",
                quantity=Quantity(value=50, unit="g"),
                confidence=0.8
            )
        ]
    )
    
    mock_openai_client.structured_complete.return_value = mock_response
    
    # Act
    result = await vision_provider.analyze_photo(
        photo_url="https://example.com/carbonara.jpg",
        hint="carbonara"
    )
    
    # Assert
    assert result.dish_name == "Spaghetti alla Carbonara"
    assert len(result.items) == 2
    
    # Verify USDA-compatible labels
    assert result.items[0].label == "pasta, cooked"
    assert result.items[1].label == "eggs"
    
    # Verify Italian display names
    assert result.items[0].display_name == "Pasta cotta"
    assert result.items[1].display_name == "Uova"
    
    # Verify OpenAI was called correctly
    mock_openai_client.structured_complete.assert_called_once()
    call_args = mock_openai_client.structured_complete.call_args
    
    # Check system prompt was provided
    assert call_args.kwargs["system_prompt"] is not None
    assert len(call_args.kwargs["system_prompt"]) > 1024  # Caching enabled
    
    # Check temperature
    assert call_args.kwargs["temperature"] == 0.1
```

---

**Next**: `05_TESTING_STRATEGY.md` - TDD approach, test examples, best practices

**Last Updated**: 22 Ottobre 2025
