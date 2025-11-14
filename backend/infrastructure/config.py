"""Configuration utilities for infrastructure layer."""

import os
from typing import Optional


def get_mongodb_uri() -> Optional[str]:
    """
    Get MongoDB URI with environment variable expansion.

    Expands ${VAR} placeholders in MONGODB_URI using environment variables.
    This allows using credentials separately in .env:

    Example .env:
        MONGODB_USER=myuser
        MONGODB_PASSWORD=mypass
        MONGODB_URI=mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@...

    Returns:
        Expanded MongoDB URI string, or None if not set
    """
    uri_template = os.getenv("MONGODB_URI")
    if not uri_template:
        return None

    # Expand ${VAR} style variables
    # Python's os.path.expandvars uses $VAR, we need ${VAR}
    user = os.getenv("MONGODB_USER", "")
    password = os.getenv("MONGODB_PASSWORD", "")

    uri = uri_template.replace("${MONGODB_USER}", user)
    uri = uri.replace("${MONGODB_PASSWORD}", password)

    return uri


def get_mongodb_database() -> str:
    """
    Get MongoDB database name.

    Returns:
        Database name from MONGODB_DATABASE env var, defaults to "nutrifit"
    """
    return os.getenv("MONGODB_DATABASE", "nutrifit")
