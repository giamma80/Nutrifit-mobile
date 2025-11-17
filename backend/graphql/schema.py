"""Main GraphQL schema factory for Nutrifit backend.

This module provides a factory function to create the complete GraphQL schema.
The actual Query and Mutation classes are defined in app.py to avoid circular
imports and maintain a single source of truth.

Usage:
    from graphql.schema import create_schema
    schema = create_schema()
"""

import strawberry


def create_schema() -> strawberry.Schema:
    """Create Strawberry schema with all integrated resolvers.

    The Query and Mutation classes are imported from app.py to ensure
    all resolvers (Meal, User, Activity, NutritionalProfile) are included.

    Returns:
        Configured Strawberry Schema instance with all domains
    """
    # Import here to avoid circular dependency
    from app import Query, Mutation

    return strawberry.Schema(
        query=Query,
        mutation=Mutation,
    )
