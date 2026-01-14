"""Unit tests for GUI presenters using unittest.mock.Mock."""

from unittest.mock import Mock, patch
import pytest

from anonymizer.ports.gui.presenters.anonymizer_presenter import AnonymizerPresenter
from anonymizer.ports.gui.presenters.entity_selection_presenter import EntitySelectionPresenter
from anonymizer.ports.gui.presenters.model_config_presenter import ModelConfigPresenter
from anonymizer.core.models import PIIEntity


class TestAnonymizerPresenter:
    """Tests for AnonymizerPresenter."""

    def test_empty_input_shows_error(self) -> None:
        """Should show error when input path is empty."""
        mock_view = Mock()
        mock_view.input_path = ""
        mock_view.output_path = "/some/output.txt"

        presenter = AnonymizerPresenter(mock_view)
        presenter.handle_anonymize()

        mock_view.show_error.assert_called_once_with(
            "Error", "Please select an input file."
        )

    def test_empty_output_shows_error(self) -> None:
        """Should show error when output path is empty."""
        mock_view = Mock()
        mock_view.input_path = "/some/input.txt"
        mock_view.output_path = ""

        presenter = AnonymizerPresenter(mock_view)
        presenter.handle_anonymize()

        mock_view.show_error.assert_called_once_with(
            "Error", "Please select an output location."
        )

    def test_no_entities_selected_shows_error(self) -> None:
        """Should show error when no entities are selected."""
        mock_view = Mock()
        mock_view.input_path = "/some/input.txt"
        mock_view.output_path = "/some/output.txt"
        mock_view.get_selected_entities.return_value = []

        presenter = AnonymizerPresenter(mock_view)
        presenter.handle_anonymize()

        mock_view.show_error.assert_called_once_with(
            "Error", "Please select at least one entity type to anonymize."
        )

    def test_non_file_input_shows_error(self) -> None:
        """Should show error when input is not a file."""
        mock_view = Mock()
        mock_view.input_path = "/some/directory"
        mock_view.output_path = "/some/output.txt"
        mock_view.get_selected_entities.return_value = ["PERSON"]
        mock_view.selected_language = "en"
        mock_view.confidence_threshold = 0.7

        presenter = AnonymizerPresenter(mock_view)

        with patch("pathlib.Path.is_file", return_value=False):
            presenter.handle_anonymize()

        mock_view.show_error.assert_called_once_with(
            "Error", "Please select a file (folder mode removed)."
        )

    def test_user_cancellation_logs_status(self) -> None:
        """Should log cancellation message when user cancels entity selection."""
        mock_view = Mock()
        mock_view.input_path = "/some/input.txt"
        mock_view.output_path = "/some/output.txt"
        mock_view.get_selected_entities.return_value = ["PERSON"]
        mock_view.selected_language = "en"
        mock_view.confidence_threshold = 0.7
        mock_view.show_entity_selection_dialog.return_value = None

        presenter = AnonymizerPresenter(mock_view)

        with patch("pathlib.Path.is_file", return_value=True), \
             patch("anonymizer.ports.gui.presenters.anonymizer_presenter.AnonymizerService") as mock_service_class:
            mock_service = Mock()
            mock_service.anonymize_file_with_selection.return_value = None
            mock_service_class.return_value = mock_service

            presenter.handle_anonymize()

        # Verify cancellation was logged
        log_calls = [call[0][0] for call in mock_view.log_status.call_args_list]
        assert any("cancelled" in call.lower() for call in log_calls)

    def test_view_mapping_no_mapping_shows_info(self) -> None:
        """Should show info when no mapping file is available."""
        mock_view = Mock()
        presenter = AnonymizerPresenter(mock_view)

        presenter.handle_view_mapping()

        mock_view.show_info.assert_called_once_with(
            "Info", "No mapping file available."
        )

    def test_get_model_info_for_language_spacy(self) -> None:
        """Should return spaCy model info."""
        mock_view = Mock()
        presenter = AnonymizerPresenter(mock_view)

        with patch("anonymizer.ports.gui.presenters.anonymizer_presenter.get_nlp_engine_type", return_value="spacy"), \
             patch("anonymizer.ports.gui.presenters.anonymizer_presenter.SUPPORTED_LANGUAGES", {"en": "en_core_web_lg"}):
            result = presenter.get_model_info_for_language("en")

        assert "en_core_web_lg" in result
        assert "spaCy" in result

    def test_get_model_info_for_language_transformers(self) -> None:
        """Should return transformers model info."""
        mock_view = Mock()
        presenter = AnonymizerPresenter(mock_view)

        mock_model = Mock()
        mock_model.name = "huggingface/some-model"

        with patch("anonymizer.ports.gui.presenters.anonymizer_presenter.get_nlp_engine_type", return_value="transformers"), \
             patch("anonymizer.ports.gui.presenters.anonymizer_presenter.get_transformers_model_for_language", return_value=mock_model):
            result = presenter.get_model_info_for_language("en")

        assert "some-model" in result
        assert "transformers" in result


class TestEntitySelectionPresenter:
    """Tests for EntitySelectionPresenter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_view = Mock()
        self.presenter = EntitySelectionPresenter(self.mock_view)
        self.entities = [
            PIIEntity(entity_type="PERSON", text="John Doe", start=0, end=8, score=0.95),
            PIIEntity(entity_type="EMAIL_ADDRESS", text="john@example.com", start=20, end=36, score=0.85),
            PIIEntity(entity_type="PHONE_NUMBER", text="555-1234", start=50, end=58, score=0.65),
        ]
        self.text = "John Doe works at john@example.com and calls 555-1234 daily."

    def test_initialize_sets_all_selected(self) -> None:
        """Should initialize with all entities selected."""
        self.presenter.initialize(self.entities, self.text, 0.7)

        display_data = self.presenter.get_entity_display_data()

        assert len(display_data) == 3
        assert all(item["selected"] for item in display_data)

    def test_toggle_selection_toggles_state(self) -> None:
        """Should toggle selection state."""
        self.presenter.initialize(self.entities, self.text, 0.7)

        # First toggle - deselect
        new_state = self.presenter.toggle_selection(0)
        assert new_state is False

        # Second toggle - select again
        new_state = self.presenter.toggle_selection(0)
        assert new_state is True

    def test_select_all_above_threshold(self) -> None:
        """Should select only entities above threshold."""
        self.presenter.initialize(self.entities, self.text, 0.8)

        # Deselect all first
        self.presenter.deselect_all()

        # Select above threshold (0.8)
        selected = self.presenter.select_all_above_threshold()

        # Only first two entities are >= 0.8
        assert len(selected) == 2
        assert 0 in selected  # 0.95 >= 0.8
        assert 1 in selected  # 0.85 >= 0.8

    def test_deselect_all(self) -> None:
        """Should deselect all entities."""
        self.presenter.initialize(self.entities, self.text, 0.7)

        deselected = self.presenter.deselect_all()

        assert len(deselected) == 3
        display_data = self.presenter.get_entity_display_data()
        assert not any(item["selected"] for item in display_data)

    def test_confirm_selection_returns_selected(self) -> None:
        """Should return only selected entities on confirm."""
        self.presenter.initialize(self.entities, self.text, 0.7)

        # Deselect the middle entity
        self.presenter.toggle_selection(1)

        result = self.presenter.confirm_selection()

        assert len(result) == 2
        assert result[0].text == "John Doe"
        assert result[1].text == "555-1234"

    def test_cancel_returns_none(self) -> None:
        """Should return None on cancel."""
        self.presenter.initialize(self.entities, self.text, 0.7)

        self.presenter.cancel()

        assert self.presenter.get_result() is None

    def test_get_entity_display_data_includes_context(self) -> None:
        """Should include context in display data."""
        self.presenter.initialize(self.entities, self.text, 0.7)

        display_data = self.presenter.get_entity_display_data()

        assert all("context" in item for item in display_data)
        # Context should contain the entity text
        assert "John Doe" in display_data[0]["context"]

    def test_get_entity_count(self) -> None:
        """Should return correct entity count."""
        self.presenter.initialize(self.entities, self.text, 0.7)

        assert self.presenter.get_entity_count() == 3

    def test_get_threshold(self) -> None:
        """Should return the initialized threshold."""
        self.presenter.initialize(self.entities, self.text, 0.75)

        assert self.presenter.get_threshold() == 0.75


class TestModelConfigPresenter:
    """Tests for ModelConfigPresenter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_view = Mock()
        self.presenter = ModelConfigPresenter(self.mock_view)

    def test_get_initial_engine_type(self) -> None:
        """Should return current engine type."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.get_nlp_engine_type", return_value="spacy"):
            result = self.presenter.get_initial_engine_type()

        assert result == "spacy"

    def test_get_available_languages(self) -> None:
        """Should return available languages."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.LANGUAGE_NAMES", {"en": "English", "de": "German"}):
            result = self.presenter.get_available_languages()

        assert "en" in result
        assert "de" in result

    def test_is_spacy_model_installed(self) -> None:
        """Should check if spaCy model is installed."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.is_model_installed", return_value=True):
            result = self.presenter.is_spacy_model_installed("en_core_web_lg")

        assert result is True

    def test_is_transformers_available(self) -> None:
        """Should check if transformers package is available."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.is_huggingface_pipelines_available", return_value=False):
            result = self.presenter.is_transformers_available()

        assert result is False

    def test_is_transformers_model_cached_empty_name(self) -> None:
        """Should return False for empty model name."""
        result = self.presenter.is_transformers_model_cached("")
        assert result is False

        result = self.presenter.is_transformers_model_cached("(none)")
        assert result is False

    def test_is_transformers_model_cached_valid_name(self) -> None:
        """Should check cache status for valid model name."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.is_transformers_model_cached", return_value=True):
            result = self.presenter.is_transformers_model_cached("some-model")

        assert result is True

    def test_validate_and_save_spacy_success(self) -> None:
        """Should save spaCy configuration successfully."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.set_nlp_engine_type") as mock_set_engine, \
             patch("anonymizer.ports.gui.presenters.model_config_presenter.set_model_for_language") as mock_set_model, \
             patch("anonymizer.ports.gui.presenters.model_config_presenter.set_transformers_model_for_language") as mock_set_transformers:

            success, message = self.presenter.validate_and_save(
                engine_type="spacy",
                spacy_selections={"en": "en_core_web_lg"},
                transformers_selections={"en": "(none)"}
            )

        assert success is True
        assert "spacy" in message
        mock_set_engine.assert_called_once_with("spacy")
        mock_set_model.assert_called_once_with("en", "en_core_web_lg")
        mock_set_transformers.assert_called_once_with("en", None)

    def test_validate_and_save_transformers_no_package(self) -> None:
        """Should fail when transformers package not installed and no progress callback."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.is_huggingface_pipelines_available", return_value=False), \
             patch("anonymizer.ports.gui.presenters.model_config_presenter.install_huggingface_pipelines", return_value=(False, "Install failed")):

            success, message = self.presenter.validate_and_save(
                engine_type="transformers",
                spacy_selections={},
                transformers_selections={}
            )

        assert success is False
        assert "transformers support" in message.lower()

    def test_validate_and_save_transformers_with_download(self) -> None:
        """Should download uncached models when saving transformers config."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.is_huggingface_pipelines_available", return_value=True), \
             patch("anonymizer.ports.gui.presenters.model_config_presenter.is_transformers_model_cached", return_value=False), \
             patch("anonymizer.ports.gui.presenters.model_config_presenter.download_transformers_model", return_value=True) as mock_download, \
             patch("anonymizer.ports.gui.presenters.model_config_presenter.set_nlp_engine_type"), \
             patch("anonymizer.ports.gui.presenters.model_config_presenter.set_model_for_language"), \
             patch("anonymizer.ports.gui.presenters.model_config_presenter.set_transformers_model_for_language"), \
             patch("anonymizer.ports.gui.presenters.model_config_presenter.AVAILABLE_TRANSFORMERS_MODELS", {}):

            success, message = self.presenter.validate_and_save(
                engine_type="transformers",
                spacy_selections={},
                transformers_selections={"en": "some-model"}
            )

        assert success is True
        mock_download.assert_called_once_with("some-model")

    def test_install_transformers_support(self) -> None:
        """Should call install function."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.install_huggingface_pipelines", return_value=(True, "Success")):
            success, message = self.presenter.install_transformers_support()

        assert success is True
        assert message == "Success"

    def test_download_transformers_model(self) -> None:
        """Should call download function."""
        with patch("anonymizer.ports.gui.presenters.model_config_presenter.download_transformers_model", return_value=True):
            result = self.presenter.download_transformers_model("some-model")

        assert result is True
