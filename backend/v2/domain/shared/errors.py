"""
Domain exceptions.

Typed exceptions for explicit error handling.
Following best practice: specific exception types for specific errors.
"""

from __future__ import annotations


# ═══════════════════════════════════════════════════════════
# BASE EXCEPTION
# ═══════════════════════════════════════════════════════════


class DomainError(Exception):
    """
    Base exception for all domain errors.

    All domain-specific exceptions inherit from this.
    Allows catching all domain errors with single except clause.
    """

    pass


# ═══════════════════════════════════════════════════════════
# MEAL DOMAIN EXCEPTIONS
# ═══════════════════════════════════════════════════════════


class MealDomainError(DomainError):
    """Base exception for meal domain."""

    pass


class RecognitionError(MealDomainError):
    """
    AI food recognition failed.

    Raised when:
    - OpenAI Vision API fails
    - No food items detected
    - Invalid image format

    Example:
        >>> raise RecognitionError("No food items detected in image")
    """

    pass


class EnrichmentError(MealDomainError):
    """
    Nutrient enrichment failed.

    Raised when:
    - USDA API fails
    - No nutrients found
    - Invalid food label

    Example:
        >>> raise EnrichmentError("USDA lookup failed for 'pizza'")
    """

    pass


class BarcodeNotFoundError(MealDomainError):
    """
    Barcode not found in database.

    Raised when:
    - OpenFoodFacts has no data for barcode
    - Invalid barcode format

    Example:
        >>> raise BarcodeNotFoundError("Barcode 123456789 not found")
    """

    pass


class InvalidQuantityError(MealDomainError):
    """
    Invalid quantity specified.

    Raised when:
    - Quantity <= 0
    - Quantity unreasonably large (>10kg)

    Example:
        >>> raise InvalidQuantityError("Quantity must be positive: -50g")
    """

    pass


class MealNotFoundError(MealDomainError):
    """
    Meal entry not found.

    Raised when:
    - Meal ID doesn't exist
    - User doesn't have permission
    - Meal was deleted

    Example:
        >>> raise MealNotFoundError("Meal abc123 not found")
    """

    pass


class AnalysisNotFoundError(MealDomainError):
    """
    Analysis not found or expired.

    Raised when:
    - Analysis ID doesn't exist
    - Analysis TTL expired (>24h)
    - Already confirmed

    Example:
        >>> raise AnalysisNotFoundError(
        ...     "Analysis xyz789 not found. It may have expired."
        ... )
    """

    pass


class IdempotencyConflictError(MealDomainError):
    """
    Idempotency key already used.

    Raised when:
    - Duplicate API request detected
    - Same meal logged twice

    Example:
        >>> raise IdempotencyConflictError(
        ...     "Meal already logged with key: abc123"
        ... )
    """

    pass


# ═══════════════════════════════════════════════════════════
# VALIDATION EXCEPTIONS
# ═══════════════════════════════════════════════════════════


class ValidationError(DomainError):
    """
    Input validation failed.

    Raised when:
    - Invalid input format
    - Missing required fields
    - Out of range values

    Example:
        >>> raise ValidationError("User ID cannot be empty")
    """

    pass


class ConflictError(DomainError):
    """
    Resource conflict detected.

    Raised when:
    - Duplicate resource
    - Concurrent modification
    - State conflict

    Example:
        >>> raise ConflictError(
        ...     "Meal already exists at this timestamp"
        ... )
    """

    pass


class NotFoundError(DomainError):
    """
    Resource not found.

    Generic not found error. Prefer specific types like
    MealNotFoundError or AnalysisNotFoundError.

    Example:
        >>> raise NotFoundError("Resource abc123 not found")
    """

    pass


class AuthorizationError(DomainError):
    """
    Authorization failed.

    Raised when:
    - User lacks permission
    - Invalid API key
    - Expired token

    Example:
        >>> raise AuthorizationError(
        ...     "User user_123 cannot access meal xyz789"
        ... )
    """

    pass


# ═══════════════════════════════════════════════════════════
# EXTERNAL SERVICE EXCEPTIONS
# ═══════════════════════════════════════════════════════════


class ExternalServiceError(DomainError):
    """
    External service call failed.

    Base class for all external service errors.

    Raised when:
    - API call fails
    - Network error
    - Service unavailable

    Example:
        >>> raise ExternalServiceError("OpenAI API failed: timeout")
    """

    pass


class RateLimitError(ExternalServiceError):
    """
    API rate limit exceeded.

    Raised when:
    - Too many requests
    - Quota exhausted
    - Throttling applied

    Example:
        >>> raise RateLimitError(
        ...     "OpenAI rate limit: 100 requests/hour"
        ... )
    """

    pass


class TimeoutError(ExternalServiceError):  # noqa: A001
    """
    API call timed out.

    Raised when:
    - Request exceeds timeout
    - No response within deadline

    Example:
        >>> raise TimeoutError("USDA API timeout after 30s")
    """

    pass


class ServiceUnavailableError(ExternalServiceError):
    """
    External service unavailable.

    Raised when:
    - Service down
    - Circuit breaker open
    - Maintenance mode

    Example:
        >>> raise ServiceUnavailableError(
        ...     "OpenFoodFacts service unavailable"
        ... )
    """

    pass


# ═══════════════════════════════════════════════════════════
# INFRASTRUCTURE EXCEPTIONS
# ═══════════════════════════════════════════════════════════


class InfrastructureError(DomainError):
    """
    Infrastructure layer error.

    Base class for database, cache, etc. errors.
    """

    pass


class DatabaseError(InfrastructureError):
    """
    Database operation failed.

    Raised when:
    - Connection lost
    - Query failed
    - Transaction rolled back

    Example:
        >>> raise DatabaseError("MongoDB connection lost")
    """

    pass


class CacheError(InfrastructureError):
    """
    Cache operation failed.

    Raised when:
    - Redis unavailable
    - Cache write failed
    - Serialization error

    Example:
        >>> raise CacheError("Redis connection failed")
    """

    pass
