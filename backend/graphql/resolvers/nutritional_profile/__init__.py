"""Nutritional Profile GraphQL resolvers.

This module exports mutations and queries for the nutritional profile domain.
"""

from graphql.resolvers.nutritional_profile.mutations import (
    NutritionalProfileMutations,
)  # noqa: E501
from graphql.resolvers.nutritional_profile.queries import NutritionalProfileQueries  # noqa: E501

__all__ = [
    "NutritionalProfileMutations",
    "NutritionalProfileQueries",
]
