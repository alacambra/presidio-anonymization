"""Unit tests for GUI presenters using unittest.mock.Mock."""

from unittest.mock import Mock, patch
import pytest

from anonymizer.ports.gui.presenters.anonymizer_presenter import AnonymizerPresenter
from anonymizer.ports.gui.presenters.entity_selection_presenter import EntitySelectionPresenter
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


class TestModelManagerPresenter:
    """Tests for ModelManagerPresenter."""

    def test_get_models_by_language_includes_download_status(self) -> None:
        """Should include download status for each model."""
        from anonymizer.ports.gui.presenters.model_manager_presenter import (
            ModelManagerPresenter,
        )

        mock_view = Mock()
        presenter = ModelManagerPresenter(mock_view)

        with patch(
            "anonymizer.ports.gui.presenters.model_manager_presenter.is_model_downloaded",
            side_effect=lambda n: n == "en_core_web_sm",
        ):
            result = presenter.get_models_by_language()

        # Find English models
        en_models = None
        for lang_code, lang_name, models in result:
            if lang_code == "en":
                en_models = models
                break

        assert en_models is not None
        sm_model = next(m for m in en_models if m["name"] == "en_core_web_sm")
        lg_model = next(m for m in en_models if m["name"] == "en_core_web_lg")
        assert sm_model["downloaded"] is True
        assert lg_model["downloaded"] is False

    def test_download_already_in_progress_shows_error(self) -> None:
        """Should show error when download already in progress."""
        from anonymizer.ports.gui.presenters.model_manager_presenter import (
            ModelManagerPresenter,
        )
        import threading

        mock_view = Mock()
        presenter = ModelManagerPresenter(mock_view)

        # Simulate active download thread
        presenter._download_thread = Mock(spec=threading.Thread)
        presenter._download_thread.is_alive.return_value = True

        presenter.download_models(["en_core_web_sm"])

        mock_view.show_error.assert_called_once()
        assert "in progress" in mock_view.show_error.call_args[0][1]

    def test_download_already_downloaded_shows_info(self) -> None:
        """Should show info when models already downloaded."""
        from anonymizer.ports.gui.presenters.model_manager_presenter import (
            ModelManagerPresenter,
        )

        mock_view = Mock()
        presenter = ModelManagerPresenter(mock_view)

        with patch(
            "anonymizer.ports.gui.presenters.model_manager_presenter.is_model_downloaded",
            return_value=True,
        ):
            presenter.download_models(["en_core_web_sm"])

        mock_view.show_info.assert_called_once()
        assert "already downloaded" in mock_view.show_info.call_args[0][1]

    def test_delete_not_downloaded_shows_info(self) -> None:
        """Should show info when trying to delete non-downloaded models."""
        from anonymizer.ports.gui.presenters.model_manager_presenter import (
            ModelManagerPresenter,
        )

        mock_view = Mock()
        presenter = ModelManagerPresenter(mock_view)

        with patch(
            "anonymizer.ports.gui.presenters.model_manager_presenter.is_model_downloaded",
            return_value=False,
        ):
            presenter.delete_models(["en_core_web_sm"])

        mock_view.show_info.assert_called_once()
        assert "not downloaded" in mock_view.show_info.call_args[0][1]

    def test_delete_success_notifies_models_changed(self) -> None:
        """Should notify view when models are deleted."""
        from anonymizer.ports.gui.presenters.model_manager_presenter import (
            ModelManagerPresenter,
        )

        mock_view = Mock()
        presenter = ModelManagerPresenter(mock_view)

        with patch(
            "anonymizer.ports.gui.presenters.model_manager_presenter.is_model_downloaded",
            return_value=True,
        ), patch(
            "anonymizer.ports.gui.presenters.model_manager_presenter.delete_model",
            return_value=(True, "Deleted"),
        ):
            presenter.delete_models(["en_core_web_sm"])

        mock_view.notify_models_changed.assert_called_once()
        mock_view.refresh_tree.assert_called_once()

    def test_cancel_download_sets_flag(self) -> None:
        """Should set cancel flag when cancel_download called."""
        from anonymizer.ports.gui.presenters.model_manager_presenter import (
            ModelManagerPresenter,
        )

        mock_view = Mock()
        presenter = ModelManagerPresenter(mock_view)

        presenter.cancel_download()

        assert presenter._cancel_download is True


class TestModelManagerDialogDestroyedState:
    """Tests for ModelManagerDialog destroyed state handling."""

    def test_schedule_ui_update_skips_when_destroyed(self) -> None:
        """Should skip UI updates when dialog is destroyed."""
        from anonymizer.ports.gui.views.model_manager_dialog import ModelManagerDialog

        # Create dialog without showing it
        mock_parent = Mock()
        dialog = ModelManagerDialog(mock_parent)
        dialog._is_destroyed = True
        dialog._dialog = Mock()

        callback = Mock()
        dialog.schedule_ui_update(callback)

        # Should not schedule the callback
        dialog._dialog.after.assert_not_called()

    def test_update_progress_skips_when_destroyed(self) -> None:
        """Should skip progress updates when dialog is destroyed."""
        from anonymizer.ports.gui.views.model_manager_dialog import ModelManagerDialog
        from unittest.mock import MagicMock

        mock_parent = Mock()
        dialog = ModelManagerDialog(mock_parent)
        dialog._is_destroyed = True
        # Use MagicMock which supports __setitem__
        dialog._progress_bar = MagicMock()
        dialog._progress_label = Mock()

        # Should not raise exception
        dialog.update_progress(10.0, 100.0, "test_model")

        # Should not update widgets (early return due to _is_destroyed)
        dialog._progress_bar.__setitem__.assert_not_called()
        dialog._progress_label.config.assert_not_called()

    def test_update_model_status_skips_when_destroyed(self) -> None:
        """Should skip status updates when dialog is destroyed."""
        from anonymizer.ports.gui.views.model_manager_dialog import ModelManagerDialog

        mock_parent = Mock()
        dialog = ModelManagerDialog(mock_parent)
        dialog._is_destroyed = True
        dialog._tree = Mock()
        dialog._item_ids = {"test_model": "item1"}

        # Should not raise exception
        dialog.update_model_status("test_model", "Downloaded", "downloaded")

        # Should not update tree
        dialog._tree.item.assert_not_called()


class TestGetAvailableLanguages:
    """Tests for get_available_languages function."""

    def test_only_checks_local_downloads(self) -> None:
        """Should only check local downloads, not pip-installed packages."""
        from anonymizer.model_storage import get_available_languages

        with patch(
            "anonymizer.model_storage.is_model_downloaded",
            side_effect=lambda n: n in ["en_core_web_sm", "de_core_news_sm"],
        ):
            result = get_available_languages()

        # Should only include languages with locally downloaded models
        assert "en" in result
        assert "de" in result
        # es and ca have no local downloads, so should not be included
        # even if they might be pip-installed
        assert "es" not in result
        assert "ca" not in result

    def test_returns_empty_when_no_downloads(self) -> None:
        """Should return empty list when no models downloaded."""
        from anonymizer.model_storage import get_available_languages

        with patch(
            "anonymizer.model_storage.is_model_downloaded",
            return_value=False,
        ):
            result = get_available_languages()

        assert result == []
