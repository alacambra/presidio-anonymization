"""Main anonymizer service - entry point for all interfaces."""

from pathlib import Path
from typing import Callable, List, Optional, Union

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
    save_excluded_entities_to_file,
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
        min_confidence: Optional[float] = None,
    ) -> None:
        """
        Initialize the anonymizer service.

        Args:
            language: Language code for PII detection (en, es, de, ca)
            selected_entities: List of entity types to detect. If None, uses all defaults.
            min_confidence: Minimum confidence threshold. If None, uses config default.
        """
        self.language = language
        self.selected_entities = selected_entities or DEFAULT_SELECTED_ENTITIES.copy()
        self.min_confidence = min_confidence if min_confidence is not None else MIN_CONFIDENCE_SCORE
        self._analyzer: Optional[PIIAnalyzer] = None

        logger.info(
            f"service initialized language:{language};entities:{len(self.selected_entities)};"
            f"threshold:{self.min_confidence}"
        )

    def _get_analyzer(self) -> PIIAnalyzer:
        """Get or create the PII analyzer (lazy initialization)."""
        if self._analyzer is None:
            self._analyzer = PIIAnalyzer(
                self.language,
                self.selected_entities,
                min_confidence=self.min_confidence
            )
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
            min_confidence_score=self.min_confidence,
        )

        if low_confidence:
            save_excluded_entities_to_file(
                entities=low_confidence,
                output_path=low_confidence_path,
                document_name=input_path.name,
                language=self.language,
                min_confidence_score=self.min_confidence,
            )

        return DocumentResult(
            input_path=str(input_path),
            output_path=str(output_path),
            mapping_path=str(mapping_path),
            language=self.language,
            entities_count=len(result.entities_found),
        )

    def anonymize_file_with_selection(
        self,
        input_path: Union[Path, str],
        output_path: Optional[Union[Path, str]] = None,
        selection_callback: Optional[Callable[[List[PIIEntity], str], Optional[List[PIIEntity]]]] = None,
    ) -> Optional[DocumentResult]:
        """
        Anonymize a document file with user selection of entities.

        Workflow:
        1. Detect all entities >= threshold
        2. Call selection_callback to let user choose entities
        3. Anonymize only selected entities
        4. Save excluded entities to *_excluded_entities.json

        Args:
            input_path: Path to the input document
            output_path: Optional path for output. If None, creates alongside input.
            selection_callback: Function that receives (entities, text) and returns selected entities.
                              If None or returns None, operation is cancelled.

        Returns:
            DocumentResult with paths and statistics, or None if cancelled
        """
        input_path = Path(input_path)
        output_path = self._resolve_output_path(input_path, output_path)
        mapping_path = self._get_mapping_path(output_path)
        excluded_path = self._get_low_confidence_path(output_path)

        logger.info(f"anonymizing file with selection input:{input_path};output:{output_path}")

        self._validate_file_extension(input_path)

        handler = get_handler(input_path.suffix)
        text = handler.read(input_path)

        # Detect all entities
        analyzer = self._get_analyzer()
        all_entities_above_threshold, below_threshold = analyzer.analyze(text)

        logger.info(
            f"detection complete above_threshold:{len(all_entities_above_threshold)};"
            f"below_threshold:{len(below_threshold)}"
        )

        # Let user select entities
        if selection_callback:
            selected_entities = selection_callback(all_entities_above_threshold, text)

            if selected_entities is None:
                # User cancelled
                logger.info("anonymization cancelled by user")
                return None
        else:
            # No callback: use all detected entities
            selected_entities = all_entities_above_threshold

        # Split into selected (anonymize) and excluded (user deselected)
        selected_set = set(id(e) for e in selected_entities)
        excluded_entities = [
            e for e in all_entities_above_threshold
            if id(e) not in selected_set
        ]

        logger.info(
            f"user selection complete selected:{len(selected_entities)};"
            f"excluded:{len(excluded_entities)}"
        )

        # Anonymize only selected entities
        mapper = PlaceholderMapper()
        anonymized_text, mappings = anonymize_text_with_mapping(text, selected_entities, mapper)

        # Write anonymized document
        handler.write(output_path, anonymized_text)

        # Save mapping (only selected entities)
        save_mapping_to_file(
            mapping=mappings,
            output_path=mapping_path,
            document_name=input_path.name,
            language=self.language,
            min_confidence_score=self.min_confidence,
        )

        # Save excluded entities (user-deselected only, with scores)
        if excluded_entities:
            save_excluded_entities_to_file(
                entities=excluded_entities,
                output_path=excluded_path,
                document_name=input_path.name,
                language=self.language,
                min_confidence_score=self.min_confidence,
            )

        return DocumentResult(
            input_path=str(input_path),
            output_path=str(output_path),
            mapping_path=str(mapping_path),
            language=self.language,
            entities_count=len(selected_entities),
        )

    def _resolve_output_path(
        self, input_path: Path, output_path: Optional[Union[Path, str]]
    ) -> Path:
        """Resolve the output path, ensuring it doesn't overwrite the input."""
        if output_path is not None:
            output_path = Path(output_path)
            # Check if output would overwrite input
            if output_path.resolve() == input_path.resolve():
                # Add .anonym before extension to prevent overwrite
                stem = input_path.stem
                suffix = input_path.suffix
                output_path = input_path.parent / f"{stem}.anonym{suffix}"
            return output_path

        # Default: add .anonym before extension
        stem = input_path.stem
        suffix = input_path.suffix
        return input_path.parent / f"{stem}.anonym{suffix}"

    def _get_mapping_path(self, output_path: Path) -> Path:
        """Get the mapping file path based on the output path."""
        return output_path.parent / f"{output_path.stem}_mapping.json"

    def _get_low_confidence_path(self, output_path: Path) -> Path:
        """Get the excluded entities file path based on the output path."""
        return output_path.parent / f"{output_path.stem}_excluded_entities.json"

    def _validate_file_extension(self, path: Path) -> None:
        """Validate that the file extension is supported."""
        if path.suffix.lower() not in SUPPORTED_FILE_EXTENSIONS:
            supported = ", ".join(SUPPORTED_FILE_EXTENSIONS)
            raise ValueError(
                f"Unsupported file type: {path.suffix}. Supported: {supported}"
            )
