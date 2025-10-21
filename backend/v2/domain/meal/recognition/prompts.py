"""
OpenAI prompts for food recognition.

IMPORTANT: System prompts are cacheable by OpenAI.
Keep static instructions in SYSTEM_PROMPT and dynamic content in user messages.
"""

from typing import Any, Optional


# ═══════════════════════════════════════════════════════════
# SYSTEM PROMPTS (Cacheable - static instructions)
# ═══════════════════════════════════════════════════════════

VISION_SYSTEM_PROMPT = """You are an expert food recognition AI specialized in Italian cuisine and international foods.

Your task: Analyze food photos and identify individual ingredients with USDA-compatible labels.

LANGUAGE REQUIREMENTS:
- dish_name: Italian name of the dish/recipe (e.g., "Spaghetti alla Carbonara")
- display_name: Italian descriptive name (e.g., "Petto di Pollo Grigliato")
- label: USDA-compatible English term for database search

CRITICAL RULES for USDA labels (English):
- Use SPECIFIC terms for accurate USDA matching
- For proteins: "chicken breast", "chicken thigh", "ground beef", "salmon fillet"
- For eggs: "whole egg", "egg white", "scrambled egg", "boiled egg", "fried egg"
- For dairy: "whole milk", "skim milk", "mozzarella cheese", "parmesan cheese"
- For grains: "white rice", "brown rice", "whole wheat bread", "white bread"
- For vegetables: "raw tomato", "cooked broccoli", "raw carrot", "cooked spinach"
- Specify cooking method when relevant: "grilled", "boiled", "fried", "raw"
- Use 1-3 words maximum, be specific but concise
- Examples:
  * Good: "chicken breast", "boiled egg", "brown rice", "grilled salmon"
  * Bad: "chicken", "egg", "rice", "fish" (too generic)
  * Bad: "grilled chicken carbonara pasta" (too complex)

Categories: grain, protein, vegetable, fruit, dairy, fat, beverage, snack, dessert, unknown

Output: JSON with:
- dish_name (Italian): Nome del piatto completo
- items: Array of ingredients
  * label (English): USDA-specific term (1-3 words)
  * display_name (Italian): Nome descrittivo ingrediente
  * quantity_g: Estimated grams
  * confidence: 0.0-1.0
  * category: Food category

Confidence guidelines:
- 0.9-1.0: Very clear, well-lit, unambiguous
- 0.7-0.9: Clear but some uncertainty on type/quantity
- 0.5-0.7: Visible but difficult estimation
- <0.5: Very uncertain (do not include)

Quantity estimation (in grams):
- Use visual context (plate size, cutlery, known portions)
- Common portions: 100g, 150g, 200g, 250g
- Be conservative if uncertain
- Consider density (leafy greens vs. meat)
"""

TEXT_EXTRACTION_SYSTEM_PROMPT = """You are an expert food extraction AI specialized in Italian cuisine and international foods.

Your task: Parse meal descriptions and extract individual ingredients with USDA-compatible labels.

LANGUAGE REQUIREMENTS:
- dish_name: Italian name of the dish/recipe (e.g., "Insalata di Pollo")
- display_name: Italian descriptive name (e.g., "Petto di Pollo Grigliato")
- label: USDA-compatible English term for database search

CRITICAL RULES for USDA labels (English):
- Use SPECIFIC terms for accurate USDA matching
- For proteins: "chicken breast", "chicken thigh", "ground beef", "salmon fillet"
- For eggs: "whole egg", "egg white", "scrambled egg", "boiled egg"
- For dairy: "whole milk", "skim milk", "mozzarella cheese", "parmesan cheese"
- For grains: "white rice", "brown rice", "whole wheat bread", "pasta"
- For vegetables: "raw tomato", "cooked broccoli", "raw spinach"
- Specify cooking method when mentioned: "grilled", "boiled", "fried", "raw"
- Use 1-3 words maximum, be specific but concise

Categories: grain, protein, vegetable, fruit, dairy, fat, beverage, snack, dessert, unknown

Output: JSON with:
- dish_name (Italian): Nome del piatto
- items: Array of ingredients
  * label (English): USDA term (1-3 words)
  * display_name (Italian): Nome ingrediente
  * quantity_g: Grams (from text or estimated)
  * confidence: 0.0-1.0
  * category: Food category

Confidence based on description:
- 0.9-1.0: Quantities specified, clear items
- 0.7-0.9: Items clear, quantities estimated
- 0.5-0.7: Vague description, rough estimation
"""


# ═══════════════════════════════════════════════════════════
# USER MESSAGE BUILDERS (Dynamic - not cached)
# ═══════════════════════════════════════════════════════════


def build_vision_user_message(image_url: str, hint: Optional[str] = None) -> str:
    """Build user message for vision analysis.

    Args:
        image_url: URL to the meal image
        hint: Optional user hint to improve recognition

    Returns:
        User message text
    """
    base_message = (
        "Analyze this food photo and identify all visible ingredients.\n\n"
        "Remember:\n"
        "- dish_name in Italian\n"
        "- display_name in Italian for each ingredient\n"
        "- label in English with USDA-specific terms (1-3 words)\n"
        "- Be specific: 'chicken breast' not 'chicken', "
        "'whole egg' not 'egg'\n"
        f"- Image URL to return: {image_url}"
    )

    if hint:
        return f"{base_message}\n\nHint: The dish might be {hint}."

    return base_message


def build_text_extraction_user_message(description: str) -> str:
    """Build user message for text extraction.

    Args:
        description: Meal description from user

    Returns:
        User message text
    """
    return f"""Extract food items from this description:

"{description}"

Remember to use USDA-compatible labels."""


# ═══════════════════════════════════════════════════════════
# JSON SCHEMA (For OpenAI structured output)
# ═══════════════════════════════════════════════════════════

VISION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "dish_name": {
            "type": "string",
            "description": "Nome del piatto in italiano (es. 'Spaghetti alla Carbonara')",
        },
        "image_url": {
            "type": "string",
            "description": "URL dell'immagine analizzata",
        },
        "items": {
            "type": "array",
            "description": "List of recognized ingredients",
            "items": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "USDA-specific English term (1-3 words, es. 'chicken breast')",
                    },
                    "display_name": {
                        "type": "string",
                        "description": "Nome ingrediente in italiano (es. 'Petto di Pollo Grigliato')",
                    },
                    "quantity_g": {
                        "type": "number",
                        "description": "Estimated quantity in grams",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Recognition confidence (0.0-1.0)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Food category",
                    },
                },
                "required": [
                    "label",
                    "display_name",
                    "quantity_g",
                    "confidence",
                ],
            },
        },
    },
    "required": ["items", "image_url"],
}

TEXT_EXTRACTION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "dish_name": {
            "type": "string",
            "description": "Nome del piatto in italiano (e.g., 'Insalata di Pollo')",
        },
        "items": {
            "type": "array",
            "description": "List of extracted ingredients",
            "items": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "USDA-specific English term (1-3 words, e.g., 'chicken breast', 'boiled egg')",
                    },
                    "display_name": {
                        "type": "string",
                        "description": "Nome ingrediente in italiano (e.g., 'Petto di Pollo')",
                    },
                    "quantity_g": {
                        "type": "number",
                        "description": "Quantity in grams",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Extraction confidence (0.0-1.0)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Food category",
                    },
                },
                "required": [
                    "label",
                    "display_name",
                    "quantity_g",
                    "confidence",
                ],
            },
        },
    },
    "required": ["items"],
}


# ═══════════════════════════════════════════════════════════
# HELPER: Build complete message arrays for OpenAI
# ═══════════════════════════════════════════════════════════


def build_vision_messages(image_url: str, hint: Optional[str] = None) -> list[dict[str, Any]]:
    """Build complete message array for vision API.

    Optimized for OpenAI prompt caching:
    - System message is cached (static instructions)
    - User message is dynamic (image + hint)

    Args:
        image_url: URL to the meal image
        hint: Optional user hint

    Returns:
        List of message dicts for OpenAI API
    """
    return [
        {"role": "system", "content": VISION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": build_vision_user_message(image_url, hint)},
                {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
            ],
        },
    ]


def build_text_extraction_messages(description: str) -> list[dict[str, Any]]:
    """Build complete message array for text extraction.

    Optimized for OpenAI prompt caching:
    - System message is cached (static instructions)
    - User message is dynamic (description)

    Args:
        description: User's meal description

    Returns:
        List of message dicts for OpenAI API
    """
    return [
        {"role": "system", "content": TEXT_EXTRACTION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_text_extraction_user_message(description),
        },
    ]
