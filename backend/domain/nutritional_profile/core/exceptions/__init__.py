"""Domain exceptions for nutritional profile."""

from .domain_errors import (
    InvalidGoalError,
    InvalidUserDataError,
    NoProgressDataError,
    ProfileAlreadyExistsError,
    ProfileDomainError,
    ProfileNotFoundError,
)

__all__ = [
    "ProfileDomainError",
    "InvalidUserDataError",
    "ProfileNotFoundError",
    "ProfileAlreadyExistsError",
    "InvalidGoalError",
    "NoProgressDataError",
]
