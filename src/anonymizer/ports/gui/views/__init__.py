"""View implementations for the GUI - humble objects with zero business logic."""

from .entity_selection_dialog import EntitySelectionDialog
from .main_window import AnonymizerView
from .model_manager_dialog import ModelManagerDialog

__all__ = [
    "AnonymizerView",
    "EntitySelectionDialog",
    "ModelManagerDialog",
]
