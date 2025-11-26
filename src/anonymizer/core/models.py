"""Data models for anonymization."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PIIEntity:
    """
    Detected PII entity in text.

    Attributes:
        entity_type: Type of PII (e.g., PERSON, EMAIL_ADDRESS)
        text: The actual PII text found
        start: Start position in original text
        end: End position in original text
        score: Confidence score from analyzer (0.0 to 1.0)
    """

    entity_type: str
    text: str
    start: int
    end: int
    score: float


@dataclass
class AnonymizationResult:
    """
    Result of text anonymization operation.

    Attributes:
        original_text: The input text before anonymization
        anonymized_text: The text with PII replaced by placeholders
        mappings: Dictionary mapping placeholders to entity details (text, entity_type, score)
        entities_found: List of detected PII entities
    """

    original_text: str
    anonymized_text: str
    mappings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    entities_found: List[PIIEntity] = field(default_factory=list)


@dataclass
class DocumentResult:
    """
    Result of document anonymization operation.

    Attributes:
        input_path: Path to the original document
        output_path: Path to the anonymized document
        mapping_path: Path to the JSON mapping file
        language: Language code used for analysis
        entities_count: Total number of entities anonymized
    """

    input_path: str
    output_path: str
    mapping_path: str
    language: str
    entities_count: int
