"""Test client USDA e normalizzazione etichette."""

from ai_models.usda_client import normalize_food_label, USDANutrient


def test_normalize_food_label_v3() -> None:
    """
    Test normalizzazione v3: pulizia base per etichette inglesi dal LLM.

    Con prompt v3, le etichette arrivano già in inglese dal LLM,
    quindi la funzione fa solo pulizia/normalizzazione.
    """

    # Test pulizia base di etichette inglesi
    assert normalize_food_label("chicken") == "chicken"
    assert normalize_food_label("CHICKEN") == "chicken"  # Lowercase
    assert normalize_food_label("  chicken  ") == "chicken"  # Trim
    assert normalize_food_label("ground-beef") == "ground-beef"  # Mantieni trattini
    assert normalize_food_label("rice") == "rice"

    # Test rimozione caratteri speciali
    assert normalize_food_label("chicken!") == "chicken"
    assert normalize_food_label("beef@#$") == "beef"
    assert normalize_food_label("fish & chips") == "fish chips"  # & rimosso

    # Test normalizzazione spazi
    assert normalize_food_label("ground   beef") == "ground beef"  # Spazi multipli → singolo

    # Test termini composti validi
    assert normalize_food_label("sweet potato") == "sweet potato"
    assert normalize_food_label("olive oil") == "olive oil"


def test_usda_nutrient_dataclass() -> None:
    """Test struttura dati USDANutrient."""

    # Test inizializzazione con valori default
    nutrient = USDANutrient()
    assert nutrient.protein == 0.0
    assert nutrient.carbs == 0.0
    assert nutrient.fat == 0.0
    assert nutrient.fiber == 0.0
    assert nutrient.sugar == 0.0
    assert nutrient.sodium == 0.0
    assert nutrient.calcium == 0.0
    assert nutrient.calories == 0.0

    # Test inizializzazione con valori specifici
    nutrient_filled = USDANutrient(
        protein=25.0,
        carbs=0.5,
        fat=4.2,
        fiber=0.0,
        sugar=0.0,
        sodium=74.5,
        calcium=15.2,
        calories=165.8,
    )

    assert nutrient_filled.protein == 25.0
    assert nutrient_filled.carbs == 0.5
    assert nutrient_filled.fat == 4.2
    assert nutrient_filled.fiber == 0.0
    assert nutrient_filled.sugar == 0.0
    assert nutrient_filled.sodium == 74.5
    assert nutrient_filled.calcium == 15.2
    assert nutrient_filled.calories == 165.8


def test_usda_nutrient_has_all_essential_fields() -> None:
    """Test che USDANutrient abbia tutti i campi essenziali."""
    nutrient = USDANutrient()

    # Verifica presenza di tutti i campi attesi
    essential_fields = [
        "protein",
        "carbs",
        "fat",
        "fiber",
        "sugar",
        "sodium",
        "calcium",
        "calories",
    ]

    for field in essential_fields:
        assert hasattr(nutrient, field), f"Campo mancante: {field}"
        assert isinstance(
            getattr(nutrient, field), (int, float)
        ), f"Campo {field} dovrebbe essere numerico"


def test_normalize_food_label_edge_cases() -> None:
    """Test casi limite per normalizzazione v3."""

    # Test stringhe vuote e spazi
    assert normalize_food_label("") == ""
    assert normalize_food_label("   ") == ""

    # Test solo caratteri speciali
    assert normalize_food_label("@#$%") == ""

    # Test numeri (dovrebbero essere mantenuti)
    assert normalize_food_label("vitamin b12") == "vitamin b12"
