"""Configuration constants for the anonymizer."""

import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SpacyModel:
    """Represents a spaCy model with its metadata."""

    name: str  # Full model name, e.g., "en_core_web_lg"
    variant: str  # sm, md, lg, trf
    size_mb: int  # Approximate size in MB
    description: str  # Short description


@dataclass
class TransformersModel:
    """Represents a HuggingFace transformers model for NER."""

    name: str  # HuggingFace model ID, e.g., "dslim/bert-base-NER"
    spacy_model: str  # spaCy model for tokenization (use small for speed)
    size_mb: int  # Approximate size in MB
    description: str  # Short description
    supported_entities: List[str] = field(
        default_factory=list
    )  # Entities this model detects


# Available HuggingFace transformer models for NER
AVAILABLE_TRANSFORMERS_MODELS: Dict[str, List[TransformersModel]] = {
    "en": [
        TransformersModel(
            "dslim/bert-base-NER",
            "en_core_web_sm",
            420,
            "BERT base NER - general purpose",
            ["PERSON", "LOCATION", "ORGANIZATION"],
        ),
        TransformersModel(
            "obi/deid_roberta_i2b2",
            "en_core_web_sm",
            500,
            "RoBERTa medical de-identification",
            [
                "PERSON",
                "LOCATION",
                "DATE_TIME",
                "ORGANIZATION",
                "AGE",
                "ID",
                "PHONE_NUMBER",
            ],
        ),
        TransformersModel(
            "StanfordAIMI/stanford-deidentifier-base",
            "en_core_web_sm",
            440,
            "Stanford medical de-identifier",
            ["PERSON", "LOCATION", "DATE_TIME", "ORGANIZATION", "AGE", "ID"],
        ),
    ],
    "es": [
        TransformersModel(
            "mrm8488/bert-spanish-cased-finetuned-ner",
            "es_core_news_sm",
            420,
            "Spanish BERT NER",
            ["PERSON", "LOCATION", "ORGANIZATION"],
        ),
        TransformersModel(
            "dccuchile/bert-base-spanish-wwm-cased-finetuned-ner",
            "es_core_news_sm",
            420,
            "Chilean Spanish BERT NER",
            ["PERSON", "LOCATION", "ORGANIZATION"],
        ),
        TransformersModel(
            "Davlan/bert-base-multilingual-cased-ner-hrl",
            "es_core_news_sm",
            700,
            "Multilingual BERT NER",
            ["PERSON", "LOCATION", "ORGANIZATION"],
        ),
    ],
    "de": [
        TransformersModel(
            "mschiesser/ner-bert-german",
            "de_core_news_sm",
            420,
            "German BERT NER",
            ["PERSON", "LOCATION", "ORGANIZATION"],
        ),
        TransformersModel(
            "fhswf/bert_de_ner",
            "de_core_news_sm",
            420,
            "German BERT NER (FHSWF)",
            ["PERSON", "LOCATION", "ORGANIZATION"],
        ),
        TransformersModel(
            "Davlan/bert-base-multilingual-cased-ner-hrl",
            "de_core_news_sm",
            700,
            "Multilingual BERT NER",
            ["PERSON", "LOCATION", "ORGANIZATION"],
        ),
    ],
    "ca": [
        TransformersModel(
            "projecte-aina/roberta-base-ca-v2-cased-ner",
            "ca_core_news_sm",
            500,
            "Catalan RoBERTa NER (AINA project)",
            ["PERSON", "LOCATION", "ORGANIZATION"],
        ),
        TransformersModel(
            "Davlan/bert-base-multilingual-cased-ner-hrl",
            "ca_core_news_sm",
            700,
            "Multilingual BERT NER",
            ["PERSON", "LOCATION", "ORGANIZATION"],
        ),
    ],
}

# Currently selected transformers model per language (None = use spaCy)
SELECTED_TRANSFORMERS_MODEL: Dict[str, Optional[str]] = {
    "en": None,
    "es": None,
    "de": None,
    "ca": None,
}

# NLP engine type: "spacy" or "transformers"
NLP_ENGINE_TYPE: str = "spacy"


def set_nlp_engine_type(engine_type: str) -> bool:
    """Set the NLP engine type globally."""
    global NLP_ENGINE_TYPE
    if engine_type not in ("spacy", "transformers"):
        return False
    NLP_ENGINE_TYPE = engine_type
    return True


def get_nlp_engine_type() -> str:
    """Get the current NLP engine type."""
    return NLP_ENGINE_TYPE


def set_transformers_model_for_language(
    lang_code: str, model_name: Optional[str]
) -> bool:
    """
    Set the transformers model for a language.

    Args:
        lang_code: Language code (en, es, de)
        model_name: HuggingFace model ID, or None to disable

    Returns True if successful, False if invalid.
    """
    if lang_code not in SELECTED_TRANSFORMERS_MODEL:
        return False
    if model_name is not None:
        available = AVAILABLE_TRANSFORMERS_MODELS.get(lang_code, [])
        valid_models = [m.name for m in available]
        if model_name not in valid_models:
            return False
    SELECTED_TRANSFORMERS_MODEL[lang_code] = model_name
    return True


def get_transformers_model_for_language(lang_code: str) -> Optional[TransformersModel]:
    """Get the selected transformers model for a language."""
    model_name = SELECTED_TRANSFORMERS_MODEL.get(lang_code)
    if model_name is None:
        return None
    available = AVAILABLE_TRANSFORMERS_MODELS.get(lang_code, [])
    for model in available:
        if model.name == model_name:
            return model
    return None


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
    """Check if a spaCy model is available (local storage or package)."""
    # Lazy import to avoid circular dependency
    from .model_storage import is_model_downloaded

    # Check local storage first
    if is_model_downloaded(model_name):
        return True

    # Fall back to package check
    try:
        import spacy.util

        return spacy.util.is_package(model_name)
    except Exception:
        return False


def is_transformers_model_cached(model_name: str) -> bool:
    """Check if a HuggingFace model is cached locally."""
    try:
        from huggingface_hub import try_to_load_from_cache
        from transformers import AutoConfig

        # Check if the config file is cached (lightweight check)
        cached = try_to_load_from_cache(model_name, "config.json")
        return cached is not None and not isinstance(cached, type(None))
    except ImportError:
        return False
    except Exception:
        return False


def download_transformers_model(model_name: str) -> bool:
    """Download a HuggingFace model to the local cache."""
    try:
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        # Download model and tokenizer
        AutoTokenizer.from_pretrained(model_name)
        AutoModelForTokenClassification.from_pretrained(model_name)
        return True
    except ImportError:
        return False
    except Exception:
        return False


def is_huggingface_pipelines_available() -> bool:
    """Check if spacy-huggingface-pipelines is installed."""
    try:
        import spacy_huggingface_pipelines  # noqa: F401

        return True
    except ImportError:
        return False


def _run_pip_install(package_spec: str, timeout: int = 300) -> tuple[bool, str]:
    """
    Install a package using pip via subprocess.

    Args:
        package_spec: Package name or URL to install
        timeout: Timeout in seconds

    Returns:
        Tuple of (success, message)
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_spec],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, "Installation complete"
        else:
            return False, result.stderr or "Installation failed"
    except subprocess.TimeoutExpired:
        return False, "Installation timed out"
    except Exception as e:
        return False, str(e)


def install_huggingface_pipelines() -> tuple[bool, str]:
    """
    Install spacy-huggingface-pipelines package.

    Returns:
        Tuple of (success, message)
    """
    return _run_pip_install("spacy-huggingface-pipelines")


def get_model_for_language(lang_code: str) -> Optional[str]:
    """Get the currently selected model for a language."""
    return SUPPORTED_LANGUAGES.get(lang_code)


def set_model_for_language(lang_code: str, model_name: str) -> bool:
    """
    Set the model for a language.

    Returns True if successful, False if invalid.
    """
    # Lazy import to avoid circular dependency
    from .logger import setup_logger
    logger = setup_logger(__name__)

    if lang_code not in AVAILABLE_MODELS:
        logger.warning(f"[set_model_for_language] invalid lang_code:{lang_code}")
        return False
    valid_models = [m.name for m in AVAILABLE_MODELS[lang_code]]
    if model_name not in valid_models:
        logger.warning(f"[set_model_for_language] invalid model:{model_name};valid:{valid_models}")
        return False

    old_model = SUPPORTED_LANGUAGES.get(lang_code)
    SUPPORTED_LANGUAGES[lang_code] = model_name
    logger.info(
        f"[set_model_for_language] updated;lang:{lang_code};old:{old_model};new:{model_name}"
    )
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

SUPPORTED_FILE_EXTENSIONS: List[str] = [".txt", ".docx", ".pdf", ".md"]

DEFAULT_LANGUAGE: str = "en"

# Minimum confidence score for PII detection (0.0 to 1.0)
# Entities with scores below this threshold will be logged but not anonymized
MIN_CONFIDENCE_SCORE: float = 0.7
