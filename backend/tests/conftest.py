import pytest
import pytest_asyncio
from typing import Generator, AsyncIterator
from metrics.ai_meal_photo import reset_all
from httpx import AsyncClient, ASGITransport
from typing import cast, Any

# Import esplicito per prevenire PendingDeprecationWarning (best effort)
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    # Placeholder: import opzionale rimosso per evitare errori mypy se assente
    pass

from app import app  # FastAPI app con schema GraphQL


@pytest.fixture(autouse=True)
def _clear_ai_env() -> Generator[None, None, None]:
    """Pulisce variabili AI_* e OPENAI_* prima di ogni test.

    Evita che valori presenti in .env (es. AI_MEAL_PHOTO_MODE=gpt4v)
    influenzino test che si aspettano adapter default. I test che
    necessitano di un valore specifico lo impostano con monkeypatch.setenv.
    """
    import os

    to_clear = [
        "AI_MEAL_PHOTO_MODE",
        "AI_GPT4V_REAL_ENABLED",
        "OPENAI_API_KEY",
        "OPENAI_VISION_MODEL",
    ]
    for k in to_clear:
        if k in os.environ:
            del os.environ[k]
    try:
        yield
    finally:
        # Non ripristiniamo i valori (ambiente test isolato); la suite intera
        # resta con stato pulito, ma manteniamo la struttura se servisse.
        pass


@pytest.fixture
def enable_nutrition_domain_v2() -> Generator[None, None, None]:
    """Fixture per abilitare temporaneamente AI_NUTRITION_V2 nei test."""
    import os

    original_value = os.environ.get("AI_NUTRITION_V2")
    os.environ["AI_NUTRITION_V2"] = "true"

    try:
        yield
    finally:
        if original_value is None:
            os.environ.pop("AI_NUTRITION_V2", None)
        else:
            os.environ["AI_NUTRITION_V2"] = original_value


@pytest.fixture
def enable_activity_domain_v2() -> Generator[None, None, None]:
    """Fixture per abilitare temporaneamente ACTIVITY_DOMAIN_V2 nei test."""
    import os

    original_value = os.environ.get("ACTIVITY_DOMAIN_V2")
    os.environ["ACTIVITY_DOMAIN_V2"] = "true"

    try:
        yield
    finally:
        if original_value is None:
            os.environ.pop("ACTIVITY_DOMAIN_V2", None)
        else:
            os.environ["ACTIVITY_DOMAIN_V2"] = original_value


@pytest.fixture
def nutrition_service() -> Generator[Any, None, None]:
    """Fixture che restituisce NutritionCalculationService con flag."""
    import os
    from domain.nutrition.application.nutrition_service import (
        get_nutrition_service,
    )

    original_value = os.environ.get("AI_NUTRITION_V2")
    os.environ["AI_NUTRITION_V2"] = "true"

    try:
        service = get_nutrition_service()
        assert service is not None, "Nutrition service should be available with feature flag"
        yield service
    finally:
        if original_value is None:
            os.environ.pop("AI_NUTRITION_V2", None)
        else:
            os.environ["AI_NUTRITION_V2"] = original_value


@pytest.fixture
def activity_integration_service() -> Generator[Any, None, None]:
    """Fixture che restituisce ActivityIntegrationService con flag."""
    import os
    from domain.activity.integration import get_activity_integration_service

    original_value = os.environ.get("ACTIVITY_DOMAIN_V2")
    os.environ["ACTIVITY_DOMAIN_V2"] = "true"

    try:
        service = get_activity_integration_service()
        assert service is not None, "Activity integration service should be available with flag"
        yield service
    finally:
        if original_value is None:
            os.environ.pop("ACTIVITY_DOMAIN_V2", None)
        else:
            os.environ["ACTIVITY_DOMAIN_V2"] = original_value


@pytest.fixture(autouse=True)
def _reset_metrics() -> Generator[None, None, None]:
    """Reset metriche prima e dopo ogni test per isolamento."""
    reset_all()
    yield
    reset_all()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Client HTTP asincrono per test GraphQL/REST.

    Usa httpx.AsyncClient con ASGITransport esplicito (scorciatoia app=
    deprecata) e base_url fittizia per coerenza nelle richieste relative.
    """
    # Cast a Any per soddisfare la firma attesa (FastAPI è compatibile ASGI)
    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as ac:
        yield ac
