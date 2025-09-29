import pytest
from typing import Generator
from metrics.ai_meal_photo import reset_all


@pytest.fixture(autouse=True)
def _reset_metrics() -> Generator[None, None, None]:
	"""Reset metriche prima e dopo ogni test per isolamento."""
	reset_all()
	yield
	reset_all()
