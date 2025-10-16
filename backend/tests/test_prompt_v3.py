"""Test per prompt v3 con etichette inglesi intelligenti."""

import pytest
from ai_models.meal_photo_prompt import parse_and_validate_v3, ParseError


def test_parse_v3_with_english_labels() -> None:
    """Test parsing v3 con etichette inglesi e display names italiani."""

    json_response = """
    {
        "dish_title": "Pollo alla griglia con riso",
        "items": [
            {
                "label": "chicken",
                "display_name": "pollo",
                "quantity": {"value": 150, "unit": "g"},
                "confidence": 0.9
            },
            {
                "label": "rice",
                "display_name": "riso basmati",
                "quantity": {"value": 100, "unit": "g"},
                "confidence": 0.85
            }
        ]
    }
    """

    dish_title, items = parse_and_validate_v3(json_response)

    # Verifica titolo piatto
    assert dish_title == "Pollo alla griglia con riso"

    # Verifica items
    assert len(items) == 2

    # Item 1 - Pollo
    chicken = items[0]
    assert chicken.label == "chicken"  # Inglese per USDA
    assert chicken.display_name == "pollo"  # Italiano per UI
    assert chicken.quantity_g == 150.0
    assert chicken.confidence == 0.9

    # Item 2 - Riso
    rice = items[1]
    assert rice.label == "rice"  # Inglese per USDA
    assert rice.display_name == "riso basmati"  # Italiano per UI
    assert rice.quantity_g == 100.0
    assert rice.confidence == 0.85


def test_parse_v3_empty_dish() -> None:
    """Test parsing v3 con piatto vuoto."""

    json_response = """
    {
        "dish_title": "",
        "items": []
    }
    """

    dish_title, items = parse_and_validate_v3(json_response)

    assert dish_title == ""
    assert len(items) == 0


def test_parse_v3_fallback_display_name() -> None:
    """Test che display_name fallback su label se mancante."""

    json_response = """
    {
        "dish_title": "Salmone grigliato",
        "items": [
            {
                "label": "salmon",
                "quantity": {"value": 200, "unit": "g"},
                "confidence": 0.8
            }
        ]
    }
    """

    dish_title, items = parse_and_validate_v3(json_response)

    assert dish_title == "Salmone grigliato"
    assert len(items) == 1

    salmon = items[0]
    assert salmon.label == "salmon"
    assert salmon.display_name == "salmon"  # Fallback su label


def test_parse_v3_missing_dish_title() -> None:
    """Test parsing v3 senza dish_title (fallback vuoto)."""

    json_response = """
    {
        "items": [
            {
                "label": "bread",
                "display_name": "pane",
                "quantity": {"value": 50, "unit": "g"},
                "confidence": 0.7
            }
        ]
    }
    """

    dish_title, items = parse_and_validate_v3(json_response)

    assert dish_title == ""  # Fallback
    assert len(items) == 1
    assert items[0].label == "bread"
    assert items[0].display_name == "pane"


def test_parse_v3_invalid_json() -> None:
    """Test parsing v3 con JSON invalido."""

    invalid_json = """
    {
        "dish_title": "Test"
        "items": []  // Manca virgola
    }
    """

    with pytest.raises(ParseError):
        parse_and_validate_v3(invalid_json)


def test_parse_v3_missing_items_array() -> None:
    """Test parsing v3 senza array items."""

    json_response = """
    {
        "dish_title": "Test dish"
    }
    """

    with pytest.raises(ParseError, match="MISSING_ITEMS_ARRAY"):
        parse_and_validate_v3(json_response)
