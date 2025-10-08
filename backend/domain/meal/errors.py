"""Domain-specific errors per meal analysis."""

from typing import Optional


class MealAnalysisError(Exception):
    """Base error per problemi nell'analisi meal."""

    def __init__(self, message: str, code: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidImageDomainError(MealAnalysisError):
    """Domain dell'immagine non nella whitelist."""

    def __init__(self, domain: str, allowed_domains: list[str]) -> None:
        message = f"Domain '{domain}' not allowed. Allowed: {allowed_domains}"
        super().__init__(message, "INVALID_IMAGE_DOMAIN")
        self.domain = domain
        self.allowed_domains = allowed_domains


class VisionServiceError(MealAnalysisError):
    """Errore nel servizio di vision (API, timeout, etc.)."""

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        super().__init__(message, "VISION_SERVICE_ERROR")
        self.original_error = original_error


class NormalizationError(MealAnalysisError):
    """Errore nella pipeline di normalizzazione."""

    def __init__(self, message: str, step: Optional[str] = None) -> None:
        super().__init__(message, "NORMALIZATION_ERROR")
        self.step = step
