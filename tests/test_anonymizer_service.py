"""Tests for AnonymizerService - core business logic."""

from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from anonymizer.core.anonymizer_service import AnonymizerService
from anonymizer.core.models import AnonymizationResult, DocumentResult, PIIEntity


class TestAnonymizerServiceInit:
    """Tests for AnonymizerService initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default values."""
        service = AnonymizerService()

        assert service.language == "en"
        assert len(service.selected_entities) > 0
        assert service.min_confidence == 0.7
        assert service._analyzer is None  # Lazy initialization

    @pytest.mark.parametrize(
        "language,expected",
        [
            ("en", "en"),
            ("es", "es"),
            ("de", "de"),
            ("ca", "ca"),
        ],
    )
    def test_init_with_language(self, language: str, expected: str) -> None:
        """Test initialization with different languages."""
        service = AnonymizerService(language=language)
        assert service.language == expected

    @pytest.mark.parametrize(
        "confidence,expected",
        [
            (0.5, 0.5),
            (0.7, 0.7),
            (0.9, 0.9),
            (0.0, 0.0),
            (1.0, 1.0),
        ],
    )
    def test_init_with_confidence(self, confidence: float, expected: float) -> None:
        """Test initialization with different confidence thresholds."""
        service = AnonymizerService(min_confidence=confidence)
        assert service.min_confidence == expected

    def test_init_with_selected_entities(self) -> None:
        """Test initialization with custom entity list."""
        entities = ["PERSON", "EMAIL_ADDRESS"]
        service = AnonymizerService(selected_entities=entities)
        assert service.selected_entities == entities

    def test_init_entities_list_is_copied(self) -> None:
        """Test that entity list is copied, not referenced."""
        entities = ["PERSON", "EMAIL_ADDRESS"]
        service = AnonymizerService(selected_entities=entities)
        entities.append("PHONE_NUMBER")
        assert "PHONE_NUMBER" not in service.selected_entities


class TestAnonymizerServiceAnonymizeText:
    """Tests for anonymize_text method."""

    @pytest.fixture
    def service(self) -> AnonymizerService:
        """Create service with mocked analyzer."""
        return AnonymizerService(language="en")

    def test_anonymize_text_returns_tuple(self, sample_text: str) -> None:
        """Test that anonymize_text returns correct tuple structure."""
        service = AnonymizerService()

        with patch.object(service, "_get_analyzer") as mock_get_analyzer:
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = ([], [])
            mock_get_analyzer.return_value = mock_analyzer

            result, low_confidence = service.anonymize_text(sample_text)

            assert isinstance(result, AnonymizationResult)
            assert isinstance(low_confidence, list)

    def test_anonymize_text_with_entities(self) -> None:
        """Test anonymization with detected entities."""
        service = AnonymizerService()
        text = "Contact John Smith at john@email.com"

        high_confidence_entities = [
            PIIEntity("PERSON", "John Smith", 8, 18, 0.9),
            PIIEntity("EMAIL_ADDRESS", "john@email.com", 22, 36, 0.95),
        ]

        with patch.object(service, "_get_analyzer") as mock_get_analyzer:
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = (high_confidence_entities, [])
            mock_get_analyzer.return_value = mock_analyzer

            result, low_confidence = service.anonymize_text(text)

            assert "<PERSON_1>" in result.anonymized_text
            assert "<EMAIL_ADDRESS_1>" in result.anonymized_text
            assert "John Smith" not in result.anonymized_text
            assert len(result.entities_found) == 2

    def test_anonymize_text_preserves_original(self) -> None:
        """Test that original text is preserved in result."""
        service = AnonymizerService()
        text = "Original text here"

        with patch.object(service, "_get_analyzer") as mock_get_analyzer:
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = ([], [])
            mock_get_analyzer.return_value = mock_analyzer

            result, _ = service.anonymize_text(text)

            assert result.original_text == text

    def test_anonymize_text_returns_low_confidence(self) -> None:
        """Test that low confidence entities are returned separately."""
        service = AnonymizerService()
        text = "Some text with entities"

        low_conf = [PIIEntity("PERSON", "Maybe Name", 0, 10, 0.5)]

        with patch.object(service, "_get_analyzer") as mock_get_analyzer:
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = ([], low_conf)
            mock_get_analyzer.return_value = mock_analyzer

            result, low_confidence = service.anonymize_text(text)

            assert len(low_confidence) == 1
            assert low_confidence[0].text == "Maybe Name"

    def test_anonymize_empty_text(self) -> None:
        """Test anonymization of empty text."""
        service = AnonymizerService()

        with patch.object(service, "_get_analyzer") as mock_get_analyzer:
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = ([], [])
            mock_get_analyzer.return_value = mock_analyzer

            result, low_confidence = service.anonymize_text("")

            assert result.anonymized_text == ""
            assert result.original_text == ""
            assert len(result.entities_found) == 0


class TestAnonymizerServiceAnonymizeFile:
    """Tests for anonymize_file method."""

    @pytest.fixture
    def mock_handler(self) -> Mock:
        """Create a mock document handler."""
        handler = Mock()
        handler.read.return_value = "John Smith is here"
        handler.write.return_value = None
        return handler

    @pytest.fixture
    def temp_input_file(self, tmp_path: Path) -> Path:
        """Create a temporary input file."""
        input_file = tmp_path / "test.txt"
        input_file.write_text("John Smith is here")
        return input_file

    def test_anonymize_file_returns_document_result(
        self, temp_input_file: Path, mock_handler: Mock
    ) -> None:
        """Test that anonymize_file returns DocumentResult."""
        service = AnonymizerService()

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "anonymize_text") as mock_anonymize,
            patch("anonymizer.core.anonymizer_service.save_mapping_to_file"),
        ):
            mock_anonymize.return_value = (
                AnonymizationResult(
                    original_text="John Smith",
                    anonymized_text="<PERSON_1>",
                    mappings={},
                    entities_found=[],
                ),
                [],
            )

            result = service.anonymize_file(temp_input_file)

            assert isinstance(result, DocumentResult)
            assert result.input_path == str(temp_input_file)

    @pytest.mark.parametrize(
        "extension",
        [".txt", ".md", ".docx", ".pdf"],
    )
    def test_anonymize_file_supported_extensions(
        self, tmp_path: Path, extension: str, mock_handler: Mock
    ) -> None:
        """Test that supported file extensions are processed."""
        input_file = tmp_path / f"test{extension}"
        input_file.write_text("content") if extension in [".txt", ".md"] else input_file.touch()

        service = AnonymizerService()

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "anonymize_text") as mock_anonymize,
            patch("anonymizer.core.anonymizer_service.save_mapping_to_file"),
        ):
            mock_anonymize.return_value = (
                AnonymizationResult("", "", {}, []),
                [],
            )

            result = service.anonymize_file(input_file)
            assert result is not None

    @pytest.mark.parametrize(
        "extension",
        [".jpg", ".png", ".exe", ".zip", ".html"],
    )
    def test_anonymize_file_unsupported_extensions(
        self, tmp_path: Path, extension: str
    ) -> None:
        """Test that unsupported file extensions raise ValueError."""
        input_file = tmp_path / f"test{extension}"
        input_file.touch()

        service = AnonymizerService()

        with pytest.raises(ValueError, match="Unsupported file type"):
            service.anonymize_file(input_file)

    def test_anonymize_file_creates_mapping_file(
        self, temp_input_file: Path, mock_handler: Mock
    ) -> None:
        """Test that mapping file is created."""
        service = AnonymizerService()

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "anonymize_text") as mock_anonymize,
            patch("anonymizer.core.anonymizer_service.save_mapping_to_file") as mock_save,
        ):
            mock_anonymize.return_value = (
                AnonymizationResult("", "", {"<PERSON_1>": {}}, []),
                [],
            )

            service.anonymize_file(temp_input_file)

            mock_save.assert_called_once()

    def test_anonymize_file_saves_low_confidence_entities(
        self, temp_input_file: Path, mock_handler: Mock
    ) -> None:
        """Test that low confidence entities are saved to file."""
        service = AnonymizerService()
        low_conf = [PIIEntity("PERSON", "Maybe", 0, 5, 0.5)]

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "anonymize_text") as mock_anonymize,
            patch("anonymizer.core.anonymizer_service.save_mapping_to_file"),
            patch("anonymizer.core.anonymizer_service.save_excluded_entities_to_file") as mock_save_excluded,
        ):
            mock_anonymize.return_value = (
                AnonymizationResult("", "", {}, []),
                low_conf,
            )

            service.anonymize_file(temp_input_file)

            mock_save_excluded.assert_called_once()

    def test_anonymize_file_no_excluded_file_when_empty(
        self, temp_input_file: Path, mock_handler: Mock
    ) -> None:
        """Test that excluded entities file is not created when list is empty."""
        service = AnonymizerService()

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "anonymize_text") as mock_anonymize,
            patch("anonymizer.core.anonymizer_service.save_mapping_to_file"),
            patch("anonymizer.core.anonymizer_service.save_excluded_entities_to_file") as mock_save_excluded,
        ):
            mock_anonymize.return_value = (
                AnonymizationResult("", "", {}, []),
                [],  # Empty low confidence list
            )

            service.anonymize_file(temp_input_file)

            mock_save_excluded.assert_not_called()


class TestAnonymizerServiceAnonymizeFileWithSelection:
    """Tests for anonymize_file_with_selection method."""

    @pytest.fixture
    def mock_handler(self) -> Mock:
        """Create a mock document handler."""
        handler = Mock()
        handler.read.return_value = "John Smith and Jane Doe"
        handler.write.return_value = None
        return handler

    @pytest.fixture
    def temp_input_file(self, tmp_path: Path) -> Path:
        """Create a temporary input file."""
        input_file = tmp_path / "test.txt"
        input_file.write_text("John Smith and Jane Doe")
        return input_file

    @pytest.fixture
    def sample_entities(self) -> List[PIIEntity]:
        """Create sample entities for testing."""
        return [
            PIIEntity("PERSON", "John Smith", 0, 10, 0.9),
            PIIEntity("PERSON", "Jane Doe", 15, 23, 0.85),
        ]

    def test_with_selection_returns_document_result(
        self, temp_input_file: Path, mock_handler: Mock, sample_entities: List[PIIEntity]
    ) -> None:
        """Test that method returns DocumentResult when not cancelled."""
        service = AnonymizerService()

        def select_all(entities: List[PIIEntity], text: str) -> List[PIIEntity]:
            return entities

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "_get_analyzer") as mock_get_analyzer,
            patch("anonymizer.core.anonymizer_service.save_mapping_to_file"),
        ):
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = (sample_entities, [])
            mock_get_analyzer.return_value = mock_analyzer

            result = service.anonymize_file_with_selection(
                temp_input_file,
                selection_callback=select_all,
            )

            assert isinstance(result, DocumentResult)

    def test_with_selection_returns_none_when_cancelled(
        self, temp_input_file: Path, mock_handler: Mock, sample_entities: List[PIIEntity]
    ) -> None:
        """Test that method returns None when user cancels."""
        service = AnonymizerService()

        def cancel_selection(entities: List[PIIEntity], text: str) -> None:
            return None

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "_get_analyzer") as mock_get_analyzer,
        ):
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = (sample_entities, [])
            mock_get_analyzer.return_value = mock_analyzer

            result = service.anonymize_file_with_selection(
                temp_input_file,
                selection_callback=cancel_selection,
            )

            assert result is None

    def test_with_selection_no_callback_uses_all_entities(
        self, temp_input_file: Path, mock_handler: Mock, sample_entities: List[PIIEntity]
    ) -> None:
        """Test that without callback, all entities are anonymized."""
        service = AnonymizerService()

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "_get_analyzer") as mock_get_analyzer,
            patch("anonymizer.core.anonymizer_service.save_mapping_to_file"),
        ):
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = (sample_entities, [])
            mock_get_analyzer.return_value = mock_analyzer

            result = service.anonymize_file_with_selection(
                temp_input_file,
                selection_callback=None,
            )

            assert result is not None
            assert result.entities_count == 2

    @pytest.mark.parametrize(
        "selected_count,expected_count",
        [
            (0, 0),
            (1, 1),
            (2, 2),
        ],
    )
    def test_with_selection_partial_selection(
        self,
        temp_input_file: Path,
        mock_handler: Mock,
        sample_entities: List[PIIEntity],
        selected_count: int,
        expected_count: int,
    ) -> None:
        """Test partial entity selection."""
        service = AnonymizerService()

        def select_partial(entities: List[PIIEntity], text: str) -> List[PIIEntity]:
            return entities[:selected_count]

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "_get_analyzer") as mock_get_analyzer,
            patch("anonymizer.core.anonymizer_service.save_mapping_to_file"),
            patch("anonymizer.core.anonymizer_service.save_excluded_entities_to_file"),
        ):
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = (sample_entities, [])
            mock_get_analyzer.return_value = mock_analyzer

            result = service.anonymize_file_with_selection(
                temp_input_file,
                selection_callback=select_partial,
            )

            assert result.entities_count == expected_count

    def test_with_selection_saves_excluded_entities(
        self, temp_input_file: Path, mock_handler: Mock, sample_entities: List[PIIEntity]
    ) -> None:
        """Test that excluded (deselected) entities are saved."""
        service = AnonymizerService()

        def select_first_only(entities: List[PIIEntity], text: str) -> List[PIIEntity]:
            return entities[:1]  # Select only first entity

        with (
            patch("anonymizer.core.anonymizer_service.get_handler", return_value=mock_handler),
            patch.object(service, "_get_analyzer") as mock_get_analyzer,
            patch("anonymizer.core.anonymizer_service.save_mapping_to_file"),
            patch("anonymizer.core.anonymizer_service.save_excluded_entities_to_file") as mock_save_excluded,
        ):
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = (sample_entities, [])
            mock_get_analyzer.return_value = mock_analyzer

            service.anonymize_file_with_selection(
                temp_input_file,
                selection_callback=select_first_only,
            )

            mock_save_excluded.assert_called_once()
            # Verify excluded entities (the second one)
            call_args = mock_save_excluded.call_args
            excluded = call_args.kwargs.get("entities") or call_args[1].get("entities")
            assert len(excluded) == 1


class TestAnonymizerServicePathResolution:
    """Tests for path resolution helper methods."""

    @pytest.mark.parametrize(
        "input_name,output_name,expected_suffix",
        [
            ("doc.txt", None, ".anonym.txt"),
            ("doc.docx", None, ".anonym.docx"),
            ("doc.pdf", None, ".anonym.pdf"),
            ("doc.md", None, ".anonym.md"),
        ],
    )
    def test_resolve_output_path_default(
        self, tmp_path: Path, input_name: str, output_name: Optional[str], expected_suffix: str
    ) -> None:
        """Test default output path generation."""
        service = AnonymizerService()
        input_path = tmp_path / input_name

        result = service._resolve_output_path(input_path, output_name)

        assert result.name.endswith(expected_suffix.split(".")[-1])
        assert ".anonym" in result.name

    def test_resolve_output_path_prevents_overwrite(self, tmp_path: Path) -> None:
        """Test that output path is modified to prevent overwriting input."""
        service = AnonymizerService()
        input_path = tmp_path / "document.txt"

        # Pass same path as output
        result = service._resolve_output_path(input_path, input_path)

        assert result != input_path
        assert ".anonym" in result.name

    def test_resolve_output_path_custom_output(self, tmp_path: Path) -> None:
        """Test custom output path is used when different from input."""
        service = AnonymizerService()
        input_path = tmp_path / "input.txt"
        output_path = tmp_path / "custom_output.txt"

        result = service._resolve_output_path(input_path, output_path)

        assert result == output_path

    def test_get_mapping_path(self, tmp_path: Path) -> None:
        """Test mapping path generation."""
        service = AnonymizerService()
        output_path = tmp_path / "document.anonym.txt"

        result = service._get_mapping_path(output_path)

        assert result.name == "document.anonym_mapping.json"
        assert result.parent == tmp_path

    def test_get_low_confidence_path(self, tmp_path: Path) -> None:
        """Test excluded entities path generation."""
        service = AnonymizerService()
        output_path = tmp_path / "document.anonym.txt"

        result = service._get_low_confidence_path(output_path)

        assert result.name == "document.anonym_excluded_entities.json"
        assert result.parent == tmp_path


class TestAnonymizerServiceLazyInitialization:
    """Tests for lazy analyzer initialization."""

    def test_analyzer_not_created_on_init(self) -> None:
        """Test that analyzer is not created during __init__."""
        service = AnonymizerService()
        assert service._analyzer is None

    def test_analyzer_created_on_first_use(self) -> None:
        """Test that analyzer is created on first _get_analyzer call."""
        service = AnonymizerService()

        with patch("anonymizer.core.anonymizer_service.PIIAnalyzer") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            result = service._get_analyzer()

            mock_class.assert_called_once()
            assert result == mock_instance

    def test_analyzer_reused_on_subsequent_calls(self) -> None:
        """Test that analyzer is reused after first creation."""
        service = AnonymizerService()

        with patch("anonymizer.core.anonymizer_service.PIIAnalyzer") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            first_result = service._get_analyzer()
            second_result = service._get_analyzer()

            # Should only be created once
            mock_class.assert_called_once()
            assert first_result is second_result
