"""Test connettività e raggiungibilità API USDA.

⚠️ LEGACY TEST - Uses old ai_models.usda_client (to be removed in Phase 8)
This test uses the legacy USDA client and enrichment service.
New tests use infrastructure/external_apis/usda/client.py instead.

TODO Phase 8: Remove this file and migrate relevant tests to:
  - tests/integration/infrastructure/test_usda_integration.py
  - tests/test_e2e_usda_enrichment.py
"""

import pytest
import asyncio
from ai_models.usda_client import USDAClient, USDANutrient  # noqa: E402
from ai_models.nutrient_enrichment import NutrientEnrichmentService  # noqa: E402

# Skip all tests in this file - legacy code uses old clients
pytestmark = pytest.mark.skip(
    reason="LEGACY: Uses old ai_models.usda_client - " "will be removed in Phase 8 cleanup"
)


# API Key fornita nella documentazione del client
USDA_API_KEY = "zqOnb4hdPJlvU1f9WBmMS8wRgphfPng9ja02KIpy"


@pytest.mark.asyncio
async def test_usda_api_connectivity() -> None:
    """Test connettività base all'API USDA."""

    async with USDAClient(api_key=USDA_API_KEY) as client:
        # Test semplice ricerca per un alimento comune
        foods = await client.search_food("chicken breast", limit=3)

        # Verifica che la API risponda
        assert isinstance(foods, list)
        print(f"\n✅ API USDA raggiungibile - Trovati {len(foods)} risultati per 'chicken breast'")

        if foods:
            # Stampa info primo risultato per debug
            first_food = foods[0]
            print(f"📋 Primo risultato: {first_food.get('description', 'N/A')}")
            print(f"🆔 FDC ID: {first_food.get('fdcId', 'N/A')}")
            print(f"📊 Data Type: {first_food.get('dataType', 'N/A')}")


@pytest.mark.asyncio
async def test_usda_nutrient_lookup() -> None:
    """Test lookup nutrienti per un FDC ID specifico."""

    async with USDAClient(api_key=USDA_API_KEY) as client:
        # Prima cerca chicken breast
        foods = await client.search_food("chicken breast", limit=1)

        if foods:
            fdc_id = foods[0].get("fdcId")
            if fdc_id:
                print(f"\n🔍 Test nutrienti per FDC ID: {fdc_id}")

                # Ottieni nutrienti
                nutrients = await client.get_nutrients(fdc_id)

                assert nutrients is not None
                assert isinstance(nutrients, USDANutrient)

                print(f"🥩 Protein: {nutrients.protein:.1f}g")
                print(f"🍞 Carbs: {nutrients.carbs:.1f}g")
                print(f"🧈 Fat: {nutrients.fat:.1f}g")
                print(f"🌾 Fiber: {nutrients.fiber:.1f}g")
                print(f"🍯 Sugar: {nutrients.sugar:.1f}g")
                print(f"🧂 Sodium: {nutrients.sodium:.1f}mg")
                print(f"🦴 Calcium: {nutrients.calcium:.1f}mg")
                print(f"⚡ Calories: {nutrients.calories:.1f}kcal")

                # Verifica che almeno protein e calories abbiano valori sensati
                assert nutrients.protein > 0, "Protein dovrebbe essere > 0 per chicken breast"
                assert nutrients.calories > 0, "Calories dovrebbe essere > 0"


@pytest.mark.asyncio
async def test_usda_search_common_foods() -> None:
    """Test ricerca per diversi alimenti comuni."""

    test_foods = ["rice", "beef", "salmon", "apple", "broccoli"]

    async with USDAClient(api_key=USDA_API_KEY) as client:
        print(f"\n🔍 Test ricerca per {len(test_foods)} alimenti comuni...")

        results = {}
        for food in test_foods:
            foods = await client.search_food(food, limit=2)
            results[food] = len(foods)
            print(f"   {food}: {len(foods)} risultati")

        # Verifica che almeno la metà degli alimenti restituisca risultati
        successful_searches = sum(1 for count in results.values() if count > 0)
        assert (
            successful_searches >= len(test_foods) // 2
        ), f"Almeno {len(test_foods)//2} ricerche dovrebbero avere successo"


@pytest.mark.asyncio
async def test_end_to_end_with_real_usda() -> None:
    """Test end-to-end con API USDA reale."""

    from ai_models.meal_photo_prompt import ParsedItem

    # Simula item parsato con etichetta inglese
    items = [
        ParsedItem(
            label="chicken",  # Etichetta inglese per USDA
            quantity_g=100.0,
            confidence=0.9,
            calories=165,  # Verrà aggiornato dall'enrichment
            source_density="medium",
            display_name="pollo",
        )
    ]

    # Test enrichment con USDA API key
    service = NutrientEnrichmentService(usda_api_key=USDA_API_KEY)
    results = await service.enrich_parsed_items(items)

    assert len(results) == 1
    result = results[0]

    print("\n🍗 Test enrichment chicken con USDA:")
    print(f"   Source: {result.source}")
    print(f"   Protein: {result.protein:.1f}g")
    print(f"   Calories: {result.calories:.1f}kcal")

    # Il risultato dovrebbe essere da heuristics o USDA, non default
    assert result.source in ["heuristic", "usda"]
    assert result.protein is not None and result.protein > 0
    assert result.calories is not None and result.calories > 0

    # Verifica statistiche
    stats = service.get_stats()
    print(f"📊 Stats: {stats}")


@pytest.mark.asyncio
async def test_usda_api_rate_limits() -> None:
    """Test comportamento con possibili rate limits."""

    async with USDAClient(api_key=USDA_API_KEY) as client:
        print("\n⏱️ Test rate limiting con 5 ricerche rapide...")

        # Fai diverse ricerche in rapida successione
        search_terms = ["chicken", "beef", "rice", "apple", "fish"]
        successful_requests = 0

        for term in search_terms:
            try:
                foods = await client.search_food(term, limit=1)
                if foods:
                    successful_requests += 1
                    print(f"   ✅ {term}: OK")
                else:
                    print(f"   ⚠️ {term}: No results")

                # Piccola pausa per essere gentili con l'API
                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"   ❌ {term}: Error - {e}")

        print(f"🎯 Richieste successful: {successful_requests}/{len(search_terms)}")

        # Almeno 3/5 dovrebbero funzionare
        assert (
            successful_requests >= 3
        ), "API dovrebbe rispondere a la maggior parte delle richieste"


@pytest.mark.asyncio
async def test_usda_api_without_key() -> None:
    """Test API senza chiave (dovrebbe funzionare ma con limiti)."""

    async with USDAClient() as client:  # No API key
        print("\n🔓 Test senza API key...")

        try:
            foods = await client.search_food("chicken", limit=1)
            print(f"   ✅ Funziona senza API key: {len(foods)} risultati")

        except Exception as e:
            print(f"   ⚠️ Errore senza API key: {e}")
            # Questo è accettabile - alcune API richiedono sempre la chiave
