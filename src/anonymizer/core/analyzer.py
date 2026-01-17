"""PII detection using Microsoft Presidio."""

from typing import List, Optional

# Register spaCy transformer factories before any model loading
try:
    from spacy_curated_transformers.pipeline import transformer as _sct  # noqa: F401
except ImportError:
    pass  # Package not installed, transformer models won't work

try:
    import spacy_transformers as _st  # noqa: F401
except ImportError:
    pass  # Package not installed

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from ..config import (
    DEFAULT_SELECTED_ENTITIES,
    MIN_CONFIDENCE_SCORE,
    SUPPORTED_LANGUAGES,
    TransformersModel,
    get_nlp_engine_type,
    get_transformers_model_for_language,
    is_model_installed,
)
from ..logger import setup_logger
from ..model_storage import download_spacy_model, get_model_path, is_model_downloaded
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
        min_confidence: Optional[float] = None,
    ) -> None:
        """
        Initialize the PII analyzer.

        Args:
            language: Language code (en, es, de, ca)
            selected_entities: List of entity types to detect. If None, uses default.
            min_confidence: Minimum confidence threshold. If None, uses config default.

        Raises:
            ValueError: If language is not supported
        """
        self._validate_language(language)
        self.language = language
        self.selected_entities = selected_entities or DEFAULT_SELECTED_ENTITIES.copy()
        self.min_confidence = min_confidence if min_confidence is not None else MIN_CONFIDENCE_SCORE
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
        engine_type = get_nlp_engine_type()
        transformers_model = get_transformers_model_for_language(self.language)

        # Use transformers engine if configured and available for this language
        if engine_type == "transformers" and transformers_model is not None:
            try:
                return self._create_transformers_engine(transformers_model)
            except (ImportError, OSError, ValueError) as e:
                # spacy-huggingface-pipelines not installed (ValueError: E002)
                # or model loading failed (OSError/ImportError)
                # Fall back to spaCy engine
                logger.warning(
                    f"[_create_engine] transformers engine failed, falling back to spaCy;"
                    f"error:{e}"
                )

        return self._create_spacy_engine()

    def _ensure_model_available(self, model_name: str) -> None:
        """
        Ensure a spaCy model is available, downloading if necessary.

        Checks local storage first, then package installation, then downloads.
        Raises OSError if model cannot be made available.
        """
        # Check local storage first
        if is_model_downloaded(model_name):
            logger.info(f"[_ensure_model_available] found in local storage;model:{model_name}")
            return

        # Check if installed as package (backward compatibility)
        if is_model_installed(model_name):
            logger.info(f"[_ensure_model_available] found as package;model:{model_name}")
            return

        # Download to local storage
        logger.info(f"[_ensure_model_available] downloading to storage;model:{model_name}")

        success, message = download_spacy_model(model_name)
        if not success:
            raise OSError(f"Failed to download model {model_name}: {message}")

        logger.info(f"[_ensure_model_available] download complete;model:{model_name}")

    def _create_spacy_engine(self) -> AnalyzerEngine:
        """Create a spaCy-based analyzer engine."""
        model_name = SUPPORTED_LANGUAGES[self.language]

        logger.info(
            f"[_create_spacy_engine] reading model from config;"
            f"language:{self.language};model:{model_name};"
            f"all_langs:{SUPPORTED_LANGUAGES}"
        )

        # Ensure model is available before calling Presidio
        self._ensure_model_available(model_name)

        # Determine model path: use local storage if available, otherwise package name
        model_path = get_model_path(model_name)
        model_spec = str(model_path) if model_path else model_name

        logger.info(
            f"[_create_spacy_engine] creating spacy engine;"
            f"language:{self.language};model:{model_name};path:{model_spec}"
        )

        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": self.language, "model_name": model_spec}
            ],
        }

        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()

        return AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=[self.language],
        )

    def _create_transformers_engine(self, model: TransformersModel) -> AnalyzerEngine:
        """Create a HuggingFace transformers-based analyzer engine."""
        from presidio_analyzer.nlp_engine import TransformersNlpEngine

        # Ensure spaCy model is available (transformers engine still needs it for tokenization)
        self._ensure_model_available(model.spacy_model)

        # Determine spaCy model path: use local storage if available, otherwise package name
        spacy_path = get_model_path(model.spacy_model)
        spacy_spec = str(spacy_path) if spacy_path else model.spacy_model

        logger.info(
            f"[_create_transformers_engine] creating transformers engine;"
            f"language:{self.language};model:{model.name};spacy:{spacy_spec}"
        )

        models = [
            {
                "lang_code": self.language,
                "model_name": {
                    "spacy": spacy_spec,
                    "transformers": model.name,
                },
            }
        ]

        nlp_engine = TransformersNlpEngine(models=models)
        nlp_engine.load()

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
            if entity.score >= self.min_confidence:
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
