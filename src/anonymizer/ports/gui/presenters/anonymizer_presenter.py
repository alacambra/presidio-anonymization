"""Presenter for the main anonymizer view - contains all business logic."""

from pathlib import Path
from typing import List, Optional

from ....config import get_nlp_engine_type, get_transformers_model_for_language, SUPPORTED_LANGUAGES
from ....core.anonymizer_service import AnonymizerService
from ....core.models import DocumentResult, PIIEntity


class AnonymizerPresenter:
    """
    Presenter for the main anonymizer window.

    Contains all business logic extracted from the original AnonymizerGUI._on_anonymize_click.
    The view is a humble object that only handles UI operations.
    """

    def __init__(self, view: "AnonymizerView") -> None:  # type: ignore[name-defined]
        """
        Initialize the presenter with a view.

        Args:
            view: The AnonymizerView instance (concrete class, not interface)
        """
        self.view = view
        self._last_mapping_path: Optional[str] = None

    def handle_anonymize(self) -> None:
        """
        Handle the anonymize button click.

        Validates inputs, creates service, and orchestrates the anonymization workflow.
        """
        # Get values from view
        input_val = self.view.input_path
        output_val = self.view.output_path

        # Validate input path
        if not input_val:
            self.view.show_error("Error", "Please select an input file.")
            return

        # Validate output path
        if not output_val:
            self.view.show_error("Error", "Please select an output location.")
            return

        # Validate entity selection
        selected_entities = self.view.get_selected_entities()
        if not selected_entities:
            self.view.show_error("Error", "Please select at least one entity type to anonymize.")
            return

        input_path = Path(input_val)

        # Validate input is a file
        if not input_path.is_file():
            self.view.show_error("Error", "Please select a file (folder mode removed).")
            return

        # Get configuration from view
        language = self.view.selected_language
        threshold = self.view.confidence_threshold

        # Log configuration
        model_info = self._get_model_info(language)
        self.view.log_status("Starting anonymization...")
        self.view.log_status(f"Language: {language}")
        self.view.log_status(model_info)
        self.view.log_status(f"Confidence threshold: {threshold:.2f}")
        self.view.log_status(f"Entity types: {', '.join(selected_entities)}")

        try:
            # Create service
            service = AnonymizerService(
                language=language,
                selected_entities=selected_entities,
                min_confidence=threshold
            )

            # Run anonymization with entity selection callback
            result = service.anonymize_file_with_selection(
                input_path,
                Path(output_val),
                selection_callback=self._create_selection_callback(threshold)
            )

            if result is None:
                self.view.log_status("Anonymization cancelled by user.")
                return

            # Handle successful result
            self._handle_result(result)
            self.view.set_mapping_button_enabled(True)
            self.view.show_success("Success", "Anonymization complete!")

        except Exception as e:
            self.view.log_status(f"Error: {str(e)}")
            self.view.show_error("Error", str(e))

    def handle_view_mapping(self) -> None:
        """Handle view mapping button click."""
        if not self._last_mapping_path:
            self.view.show_info("Info", "No mapping file available.")
            return

        try:
            import json
            with open(self._last_mapping_path, "r", encoding="utf-8") as f:
                mapping_data = json.load(f)

            self.view.show_mapping_window(mapping_data)

        except Exception as e:
            self.view.show_error("Error", f"Could not load mapping: {e}")

    def get_model_info_for_language(self, language: str) -> str:
        """Get model info string for display."""
        return self._get_model_info(language)

    def _get_model_info(self, language: str) -> str:
        """Get a description of the currently configured model for a language."""
        engine_type = get_nlp_engine_type()

        if engine_type == "transformers":
            transformers_model = get_transformers_model_for_language(language)
            if transformers_model is not None:
                short_name = transformers_model.name.split("/")[-1]
                return f"Model: {short_name} (transformers)"

        spacy_model = SUPPORTED_LANGUAGES.get(language, "")
        if spacy_model:
            return f"Model: {spacy_model} (spaCy)"
        return "Model: not configured"

    def _create_selection_callback(self, threshold: float):
        """Create a callback for entity selection that routes through the view."""
        def callback(entities: List[PIIEntity], text: str) -> Optional[List[PIIEntity]]:
            return self.view.show_entity_selection_dialog(entities, text, threshold)
        return callback

    def _handle_result(self, result: DocumentResult) -> None:
        """Handle successful anonymization result."""
        self.view.log_status(f"Output: {result.output_path}")
        self.view.log_status(f"Mapping: {result.mapping_path}")
        self.view.log_status(f"Entities anonymized: {result.entities_count}")
        self._last_mapping_path = result.mapping_path
