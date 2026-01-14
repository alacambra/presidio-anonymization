"""Presenter for the entity selection dialog - contains selection logic."""

from typing import Dict, List, Optional

from ....core.models import PIIEntity


class EntitySelectionPresenter:
    """
    Presenter for the entity selection dialog.

    Contains all business logic for managing entity selection state,
    filtering by threshold, and extracting context for display.
    """

    def __init__(self, view: "EntitySelectionDialog") -> None:  # type: ignore[name-defined]
        """
        Initialize the presenter with a view.

        Args:
            view: The EntitySelectionDialog instance (concrete class)
        """
        self.view = view
        self._entities: List[PIIEntity] = []
        self._text: str = ""
        self._threshold: float = 0.7
        self._selection_state: Dict[int, bool] = {}
        self._result: Optional[List[PIIEntity]] = None

    def initialize(
        self,
        entities: List[PIIEntity],
        text: str,
        threshold: float
    ) -> None:
        """
        Initialize the presenter with entity data.

        Args:
            entities: List of detected PII entities
            text: Original document text for context extraction
            threshold: Confidence threshold for filtering
        """
        self._entities = entities
        self._text = text
        self._threshold = threshold
        self._selection_state = {idx: True for idx in range(len(entities))}
        self._result = None

    def get_entity_display_data(self) -> List[Dict]:
        """
        Get entity data formatted for display.

        Returns:
            List of dicts with entity display info including context
        """
        display_data = []
        for idx, entity in enumerate(self._entities):
            context = self._extract_context(entity)
            display_data.append({
                "id": idx,
                "selected": self._selection_state[idx],
                "text": entity.text,
                "entity_type": entity.entity_type,
                "score": entity.score,
                "context": context
            })
        return display_data

    def toggle_selection(self, entity_id: int) -> bool:
        """
        Toggle selection state for an entity.

        Args:
            entity_id: Index of the entity to toggle

        Returns:
            New selection state (True = selected)
        """
        current = self._selection_state.get(entity_id, True)
        new_state = not current
        self._selection_state[entity_id] = new_state
        return new_state

    def select_all_above_threshold(self) -> List[int]:
        """
        Select all entities with score >= threshold.

        Returns:
            List of entity IDs that were selected
        """
        selected_ids = []
        for idx, entity in enumerate(self._entities):
            if entity.score >= self._threshold:
                self._selection_state[idx] = True
                selected_ids.append(idx)
        return selected_ids

    def deselect_all(self) -> List[int]:
        """
        Deselect all entities.

        Returns:
            List of all entity IDs (all deselected)
        """
        all_ids = list(self._selection_state.keys())
        for idx in all_ids:
            self._selection_state[idx] = False
        return all_ids

    def confirm_selection(self) -> List[PIIEntity]:
        """
        Confirm the current selection and return selected entities.

        Returns:
            List of selected PIIEntity objects
        """
        self._result = [
            self._entities[idx]
            for idx, is_selected in self._selection_state.items()
            if is_selected
        ]
        return self._result

    def cancel(self) -> None:
        """Cancel selection - result will be None."""
        self._result = None

    def get_result(self) -> Optional[List[PIIEntity]]:
        """
        Get the final selection result.

        Returns:
            List of selected entities, or None if cancelled
        """
        return self._result

    def get_entity_count(self) -> int:
        """Get total number of entities."""
        return len(self._entities)

    def get_threshold(self) -> float:
        """Get the confidence threshold."""
        return self._threshold

    def _extract_context(self, entity: PIIEntity, context_length: int = 50) -> str:
        """
        Extract surrounding context for an entity.

        Args:
            entity: Entity to extract context for
            context_length: Number of characters to show before/after

        Returns:
            Context string with entity highlighted
        """
        start = max(0, entity.start - context_length)
        end = min(len(self._text), entity.end + context_length)

        context = self._text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(self._text):
            context = context + "..."

        # Replace newlines/tabs with spaces for display
        context = " ".join(context.split())

        return context
