"""Configuration constants for the anonymizer."""

from typing import Dict, List

SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "en_core_web_sm",
    "es": "es_core_news_sm",
    "de": "de_core_news_md",
    "ca": "ca_core_news_lg",
}

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
