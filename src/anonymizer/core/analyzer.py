"""PII detection using Microsoft Presidio."""

from typing import List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from ..config import DEFAULT_SELECTED_ENTITIES, MIN_CONFIDENCE_SCORE, SUPPORTED_LANGUAGES
from ..logger import setup_logger
from .models import PIIEntity

logger = setup_logger(__name__)


class PIIAnalyzer:
    """
    Analyzer for detecting PII in text using Presidio.

    Supports multiple languages and configurable entity types.
    """

    def __init__(
        self,
        language: str = "en",
        selected_entities: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the PII analyzer.

        Args:
            language: Language code (en, es, de, ca)
            selected_entities: List of entity types to detect. If None, uses default.

        Raises:
            ValueError: If language is not supported
        """
        self._validate_language(language)
        self.language = language
        self.selected_entities = selected_entities or DEFAULT_SELECTED_ENTITIES.copy()
        self._engine: Optional[AnalyzerEngine] = None

    def _validate_language(self, language: str) -> None:
        """Validate that language is supported."""
        if language not in SUPPORTED_LANGUAGES:
            supported = ", ".join(SUPPORTED_LANGUAGES.keys())
            raise ValueError(
                f"Unsupported language: {language}. Supported: {supported}"
            )

    def _get_engine(self) -> AnalyzerEngine:
        """Get or create the analyzer engine (lazy initialization)."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self) -> AnalyzerEngine:
        """Create a new Presidio analyzer engine."""
        logger.info(
            f"[_create_engine] creating analyzer engine;language:{self.language};model:{SUPPORTED_LANGUAGES[self.language]}"
        )

        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": self.language, "model_name": SUPPORTED_LANGUAGES[self.language]}
            ],
        }

        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()

        return AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=[self.language],
        )

    def analyze(self, text: str) -> tuple[List[PIIEntity], List[PIIEntity]]:
        """
        Analyze text and detect PII entities.

        Args:
            text: Text to analyze for PII

        Returns:
            Tuple of (high_confidence_entities, low_confidence_entities)
            High confidence: score >= MIN_CONFIDENCE_SCORE (will be anonymized)
            Low confidence: score < MIN_CONFIDENCE_SCORE (logged only)
        """
        engine = self._get_engine()

        results: List[RecognizerResult] = engine.analyze(
            text=text,
            language=self.language,
            entities=self.selected_entities,
        )

        all_entities = self._convert_results_to_entities(results, text)
        high_confidence, low_confidence = self._split_by_confidence(all_entities)

        logger.info(
            f"[analyze] analysis complete;high_confidence:{len(high_confidence)};"
            f"low_confidence:{len(low_confidence)};text_length:{len(text)}"
        )

        return high_confidence, low_confidence

    def _split_by_confidence(
        self, entities: List[PIIEntity]
    ) -> tuple[List[PIIEntity], List[PIIEntity]]:
        """Split entities into high and low confidence based on threshold."""
        high_confidence: List[PIIEntity] = []
        low_confidence: List[PIIEntity] = []

        for entity in entities:
            if entity.score >= MIN_CONFIDENCE_SCORE:
                high_confidence.append(entity)
            else:
                low_confidence.append(entity)

        return high_confidence, low_confidence

    def _convert_results_to_entities(
        self, results: List[RecognizerResult], text: str
    ) -> List[PIIEntity]:
        """Convert Presidio results to PIIEntity objects."""
        entities: List[PIIEntity] = []

        for result in results:
            entity = PIIEntity(
                entity_type=result.entity_type,
                text=text[result.start:result.end],
                start=result.start,
                end=result.end,
                score=result.score,
            )
            entities.append(entity)

        return self._sort_entities_by_position(entities)

    def _sort_entities_by_position(self, entities: List[PIIEntity]) -> List[PIIEntity]:
        """Sort entities by their position in text (start index)."""
        return sorted(entities, key=lambda e: e.start)
