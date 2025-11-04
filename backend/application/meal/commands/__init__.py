"""CQRS Commands for meal domain."""

from .analyze_photo import (
    AnalyzeMealPhotoCommand,
    AnalyzeMealPhotoCommandHandler,
)
from .analyze_barcode import (
    AnalyzeMealBarcodeCommand,
    AnalyzeMealBarcodeCommandHandler,
)
from .confirm_analysis import (
    ConfirmAnalysisCommand,
    ConfirmAnalysisCommandHandler,
)
from .update_meal import (
    UpdateMealCommand,
    UpdateMealCommandHandler,
)
from .delete_meal import (
    DeleteMealCommand,
    DeleteMealCommandHandler,
)

__all__ = [
    # Analyze commands
    "AnalyzeMealPhotoCommand",
    "AnalyzeMealPhotoCommandHandler",
    "AnalyzeMealBarcodeCommand",
    "AnalyzeMealBarcodeCommandHandler",
    # Confirmation command
    "ConfirmAnalysisCommand",
    "ConfirmAnalysisCommandHandler",
    # Update/Delete commands
    "UpdateMealCommand",
    "UpdateMealCommandHandler",
    "DeleteMealCommand",
    "DeleteMealCommandHandler",
]
