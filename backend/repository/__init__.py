"""Repository package for persistence abstractions.

In-memory meal repository (dev/test). L'assenza di questo file rompeva
l'import in deploy (`ModuleNotFoundError: repository`).
"""

from . import meals  # noqa: F401

__all__ = ["meals"]
