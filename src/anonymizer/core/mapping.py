"""Placeholder mapping logic for anonymization."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..logger import setup_logger
from .models import PIIEntity

logger = setup_logger(__name__)


class PlaceholderMapper:
    """
    Manages placeholder generation and mapping for PII anonymization.

    Ensures consistent placeholder assignment: same PII value
    receives the same placeholder within a document.
    """

    def __init__(self) -> None:
        """Initialize the placeholder mapper."""
        self._value_to_placeholder: Dict[str, str] = {}
        self._placeholder_to_value: Dict[str, Dict[str, Any]] = {}
        self._type_counters: Dict[str, int] = {}

    def get_placeholder(self, entity: PIIEntity) -> str:
        """
        Get or create a placeholder for a PII entity.

        Same value always returns the same placeholder (deduplication).

        Args:
            entity: The PII entity to get a placeholder for

        Returns:
            Placeholder string like <PERSON_1>
        """
        key = self._create_lookup_key(entity)

        if key in self._value_to_placeholder:
            return self._value_to_placeholder[key]

        placeholder = self._generate_new_placeholder(entity.entity_type)
        self._register_mapping(key, placeholder, entity)

        return placeholder

    def _create_lookup_key(self, entity: PIIEntity) -> str:
        """Create a unique key for looking up existing placeholders."""
        return f"{entity.entity_type}:{entity.text}"

    def _generate_new_placeholder(self, entity_type: str) -> str:
        """Generate a new numbered placeholder for an entity type."""
        count = self._increment_counter(entity_type)
        return f"<{entity_type}_{count}>"

    def _increment_counter(self, entity_type: str) -> int:
        """Increment and return the counter for an entity type."""
        if entity_type not in self._type_counters:
            self._type_counters[entity_type] = 0
        self._type_counters[entity_type] += 1
        return self._type_counters[entity_type]

    def _register_mapping(self, key: str, placeholder: str, entity: PIIEntity) -> None:
        """Register a new placeholder mapping with entity details."""
        self._value_to_placeholder[key] = placeholder
        self._placeholder_to_value[placeholder] = {
            "text": entity.text,
            "entity_type": entity.entity_type,
            "score": round(entity.score, 4),
        }

    def get_mappings(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all placeholder-to-value mappings with details.

        Returns:
            Dictionary mapping placeholders to entity details (text, entity_type, score)
        """
        return dict(self._placeholder_to_value)

    def reset(self) -> None:
        """Reset all mappings and counters."""
        self._value_to_placeholder.clear()
        self._placeholder_to_value.clear()
        self._type_counters.clear()


def anonymize_text_with_mapping(
    text: str, entities: List[PIIEntity], mapper: PlaceholderMapper
) -> Tuple[str, Dict[str, Dict[str, Any]]]:
    """
    Replace PII entities in text with placeholders.

    Processes entities from end to start to maintain correct positions.

    Args:
        text: Original text containing PII
        entities: List of detected PII entities (sorted by position)
        mapper: PlaceholderMapper instance for consistent mapping

    Returns:
        Tuple of (anonymized_text, mappings_dict)
    """
    sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)

    result = text
    for entity in sorted_entities:
        placeholder = mapper.get_placeholder(entity)
        result = replace_entity_in_text(result, entity, placeholder)

    logger.info(
        f"text anonymized original_length:{len(text)};anonymized_length:{len(result)}"
    )

    return result, mapper.get_mappings()


def replace_entity_in_text(text: str, entity: PIIEntity, placeholder: str) -> str:
    """Replace a single entity in text with its placeholder."""
    return text[:entity.start] + placeholder + text[entity.end:]


def save_mapping_to_file(
    mapping: Dict[str, Dict[str, Any]],
    output_path: Path,
    document_name: str,
    language: str,
    min_confidence_score: float,
) -> None:
    """
    Save the mapping dictionary to a JSON file.

    Args:
        mapping: Placeholder to entity details mapping (text, entity_type, score)
        output_path: Path where to save the JSON file
        document_name: Name of the original document
        language: Language code used for analysis
        min_confidence_score: Minimum confidence threshold used
    """
    mapping_data = {
        "document": document_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "language": language,
        "min_confidence_score": min_confidence_score,
        "mappings": mapping,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapping_data, f, indent=2, ensure_ascii=False)

    logger.info(
        f"mapping saved path:{output_path};entries:{len(mapping)}"
    )


def save_low_confidence_to_file(
    entities: List[PIIEntity],
    output_path: Path,
    document_name: str,
    language: str,
    min_confidence_score: float,
) -> None:
    """
    Save low-confidence entities to a JSON file for review.

    These entities were detected but not anonymized due to low confidence scores.

    Args:
        entities: List of low-confidence PII entities
        output_path: Path where to save the JSON file
        document_name: Name of the original document
        language: Language code used for analysis
        min_confidence_score: Minimum confidence threshold used
    """
    low_confidence_data = {
        "document": document_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "language": language,
        "min_confidence_score": min_confidence_score,
        "note": "These entities were detected but NOT anonymized due to scores below threshold",
        "entities": [
            {
                "text": entity.text,
                "entity_type": entity.entity_type,
                "score": round(entity.score, 4),
                "start": entity.start,
                "end": entity.end,
            }
            for entity in entities
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(low_confidence_data, f, indent=2, ensure_ascii=False)

    logger.info(
        f"low confidence matches saved path:{output_path};entries:{len(entities)}"
    )


def load_mapping_from_file(mapping_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load a mapping dictionary from a JSON file.

    Args:
        mapping_path: Path to the mapping JSON file

    Returns:
        Placeholder to entity details mapping dictionary
    """
    with open(mapping_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("mappings", {})
