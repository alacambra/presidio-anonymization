"""Main anonymizer service - entry point for all interfaces."""

from pathlib import Path
from typing import List, Optional, Union

from ..config import (
    DEFAULT_LANGUAGE,
    DEFAULT_SELECTED_ENTITIES,
    MIN_CONFIDENCE_SCORE,
    SUPPORTED_FILE_EXTENSIONS,
)
from ..handlers import get_handler
from ..logger import setup_logger
from .analyzer import PIIAnalyzer
from .mapping import (
    PlaceholderMapper,
    anonymize_text_with_mapping,
    save_low_confidence_to_file,
    save_mapping_to_file,
)
from .models import AnonymizationResult, DocumentResult, PIIEntity

logger = setup_logger(__name__)


class AnonymizerService:
    """
    Main service for document anonymization.

    Used by both CLI and GUI - they call the same methods.
    Orchestrates the analyzer, mapping, and document handlers.
    """

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
        selected_entities: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the anonymizer service.

        Args:
            language: Language code for PII detection (en, es, de, ca)
            selected_entities: List of entity types to detect. If None, uses all defaults.
        """
        self.language = language
        self.selected_entities = selected_entities or DEFAULT_SELECTED_ENTITIES.copy()
        self._analyzer: Optional[PIIAnalyzer] = None

        logger.info(
            f"service initialized language:{language};entities:{len(self.selected_entities)}"
        )

    def _get_analyzer(self) -> PIIAnalyzer:
        """Get or create the PII analyzer (lazy initialization)."""
        if self._analyzer is None:
            self._analyzer = PIIAnalyzer(self.language, self.selected_entities)
        return self._analyzer

    def anonymize_text(self, text: str) -> tuple[AnonymizationResult, List[PIIEntity]]:
        """
        Anonymize plain text and return result with mappings.

        Args:
            text: Plain text string to anonymize

        Returns:
            Tuple of (AnonymizationResult, low_confidence_entities)
            - AnonymizationResult: contains anonymized_text, mappings, and high-confidence entities
            - low_confidence_entities: entities below threshold, not anonymized
        """
        logger.info(f"anonymizing text length:{len(text)}")

        analyzer = self._get_analyzer()
        high_confidence, low_confidence = analyzer.analyze(text)

        mapper = PlaceholderMapper()
        anonymized_text, mappings = anonymize_text_with_mapping(text, high_confidence, mapper)

        result = AnonymizationResult(
            original_text=text,
            anonymized_text=anonymized_text,
            mappings=mappings,
            entities_found=high_confidence,
        )

        return result, low_confidence

    def anonymize_file(
        self,
        input_path: Union[Path, str],
        output_path: Optional[Union[Path, str]] = None,
    ) -> DocumentResult:
        """
        Anonymize a document file (txt, docx, pdf).

        Args:
            input_path: Path to the input document
            output_path: Optional path for output. If None, creates alongside input.

        Returns:
            DocumentResult with paths and statistics
        """
        input_path = Path(input_path)
        output_path = self._resolve_output_path(input_path, output_path)
        mapping_path = self._get_mapping_path(output_path)
        low_confidence_path = self._get_low_confidence_path(output_path)

        logger.info(f"anonymizing file input:{input_path};output:{output_path}")

        self._validate_file_extension(input_path)

        handler = get_handler(input_path.suffix)
        text = handler.read(input_path)

        result, low_confidence = self.anonymize_text(text)

        handler.write(output_path, result.anonymized_text)

        save_mapping_to_file(
            mapping=result.mappings,
            output_path=mapping_path,
            document_name=input_path.name,
            language=self.language,
            min_confidence_score=MIN_CONFIDENCE_SCORE,
        )

        if low_confidence:
            save_low_confidence_to_file(
                entities=low_confidence,
                output_path=low_confidence_path,
                document_name=input_path.name,
                language=self.language,
                min_confidence_score=MIN_CONFIDENCE_SCORE,
            )

        return DocumentResult(
            input_path=str(input_path),
            output_path=str(output_path),
            mapping_path=str(mapping_path),
            language=self.language,
            entities_count=len(result.entities_found),
        )

    def anonymize_directory(
        self,
        input_dir: Union[Path, str],
        output_dir: Union[Path, str],
    ) -> List[DocumentResult]:
        """
        Anonymize all supported files in a directory.

        Args:
            input_dir: Directory containing documents to anonymize
            output_dir: Directory where to save anonymized documents

        Returns:
            List of DocumentResult for each processed file
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        logger.info(f"anonymizing directory input_dir:{input_dir};output_dir:{output_dir}")

        self._validate_directory(input_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results: List[DocumentResult] = []
        files = self._find_supported_files(input_dir)

        for file_path in files:
            relative_path = file_path.relative_to(input_dir)
            output_path = output_dir / relative_path

            result = self.anonymize_file(file_path, output_path)
            results.append(result)

        logger.info(f"directory anonymization complete files_processed:{len(results)}")

        return results

    def _resolve_output_path(
        self, input_path: Path, output_path: Optional[Union[Path, str]]
    ) -> Path:
        """Resolve the output path, creating a default if not provided."""
        if output_path is not None:
            return Path(output_path)

        stem = input_path.stem
        suffix = input_path.suffix
        return input_path.parent / f"{stem}_anonymized{suffix}"

    def _get_mapping_path(self, output_path: Path) -> Path:
        """Get the mapping file path based on the output path."""
        return output_path.parent / f"{output_path.stem}_mapping.json"

    def _get_low_confidence_path(self, output_path: Path) -> Path:
        """Get the low-confidence matches file path based on the output path."""
        return output_path.parent / f"{output_path.stem}_low_confidence.json"

    def _validate_file_extension(self, path: Path) -> None:
        """Validate that the file extension is supported."""
        if path.suffix.lower() not in SUPPORTED_FILE_EXTENSIONS:
            supported = ", ".join(SUPPORTED_FILE_EXTENSIONS)
            raise ValueError(
                f"Unsupported file type: {path.suffix}. Supported: {supported}"
            )

    def _validate_directory(self, path: Path) -> None:
        """Validate that the path is a directory."""
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")

    def _find_supported_files(self, directory: Path) -> List[Path]:
        """Find all supported files in a directory recursively."""
        files: List[Path] = []

        for ext in SUPPORTED_FILE_EXTENSIONS:
            files.extend(directory.rglob(f"*{ext}"))

        return sorted(files)
