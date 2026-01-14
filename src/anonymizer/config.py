"""Configuration constants for the anonymizer."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SpacyModel:
    """Represents a spaCy model with its metadata."""

    name: str  # Full model name, e.g., "en_core_web_lg"
    variant: str  # sm, md, lg, trf
    size_mb: int  # Approximate size in MB
    description: str  # Short description


# Available spaCy models for each language
AVAILABLE_MODELS: Dict[str, List[SpacyModel]] = {
    "en": [
        SpacyModel("en_core_web_sm", "sm", 12, "Small - CPU optimized"),
        SpacyModel("en_core_web_md", "md", 40, "Medium - balanced"),
        SpacyModel("en_core_web_lg", "lg", 560, "Large - better accuracy"),
        SpacyModel("en_core_web_trf", "trf", 440, "Transformer - best accuracy"),
    ],
    "es": [
        SpacyModel("es_core_news_sm", "sm", 12, "Small - CPU optimized"),
        SpacyModel("es_core_news_md", "md", 40, "Medium - balanced"),
        SpacyModel("es_core_news_lg", "lg", 560, "Large - better accuracy"),
        SpacyModel("es_dep_news_trf", "trf", 450, "Transformer - best accuracy"),
    ],
    "de": [
        SpacyModel("de_core_news_sm", "sm", 12, "Small - CPU optimized"),
        SpacyModel("de_core_news_md", "md", 40, "Medium - balanced"),
        SpacyModel("de_core_news_lg", "lg", 540, "Large - better accuracy"),
        SpacyModel("de_dep_news_trf", "trf", 440, "Transformer - best accuracy"),
    ],
    "ca": [
        SpacyModel("ca_core_news_sm", "sm", 12, "Small - CPU optimized"),
        SpacyModel("ca_core_news_md", "md", 40, "Medium - balanced"),
        SpacyModel("ca_core_news_lg", "lg", 540, "Large - better accuracy"),
        SpacyModel("ca_core_news_trf", "trf", 440, "Transformer - best accuracy"),
    ],
}

# Language display names
LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "ca": "Catalan",
}

# Currently selected model for each language
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "en_core_web_trf",
    "es": "es_dep_news_trf",
    "de": "de_dep_news_trf",
    "ca": "ca_core_news_trf",
}


def is_model_installed(model_name: str) -> bool:
    """Check if a spaCy model is installed."""
    try:
        import spacy.util

        return spacy.util.is_package(model_name)
    except Exception:
        return False


def get_model_for_language(lang_code: str) -> Optional[str]:
    """Get the currently selected model for a language."""
    return SUPPORTED_LANGUAGES.get(lang_code)


def set_model_for_language(lang_code: str, model_name: str) -> bool:
    """
    Set the model for a language.

    Returns True if successful, False if invalid.
    """
    if lang_code not in AVAILABLE_MODELS:
        return False
    valid_models = [m.name for m in AVAILABLE_MODELS[lang_code]]
    if model_name not in valid_models:
        return False
    SUPPORTED_LANGUAGES[lang_code] = model_name
    return True

# All available entity types for PII detection
SUPPORTED_ENTITIES: List[str] = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "LOCATION",
    "DATE_TIME",
    "NRP",
]

# Default selected entities (all enabled by default)
DEFAULT_SELECTED_ENTITIES: List[str] = SUPPORTED_ENTITIES.copy()

SUPPORTED_FILE_EXTENSIONS: List[str] = [
    ".txt",
    ".docx",
    ".pdf",
    ".md"
]

DEFAULT_LANGUAGE: str = "en"

# Minimum confidence score for PII detection (0.0 to 1.0)
# Entities with scores below this threshold will be logged but not anonymized
MIN_CONFIDENCE_SCORE: float = 0.7
