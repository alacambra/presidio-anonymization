"""Tests for placeholder mapping logic."""

import json
import tempfile
from pathlib import Path

import pytest

from anonymizer.core.mapping import (
    PlaceholderMapper,
    anonymize_text_with_mapping,
    load_mapping_from_file,
    save_mapping_to_file,
)
from anonymizer.core.models import PIIEntity


class TestPlaceholderMapper:
    """Tests for PlaceholderMapper class."""

    def test_get_placeholder_creates_new(self) -> None:
        """Test that new entities get unique placeholders."""
        mapper = PlaceholderMapper()

        entity1 = PIIEntity("PERSON", "John", 0, 4, 0.9)
        entity2 = PIIEntity("PERSON", "Jane", 10, 14, 0.9)

        placeholder1 = mapper.get_placeholder(entity1)
        placeholder2 = mapper.get_placeholder(entity2)

        assert placeholder1 == "<PERSON_1>"
        assert placeholder2 == "<PERSON_2>"

    def test_same_value_same_placeholder(self) -> None:
        """Test that same value gets same placeholder (deduplication)."""
        mapper = PlaceholderMapper()

        entity1 = PIIEntity("PERSON", "John", 0, 4, 0.9)
        entity2 = PIIEntity("PERSON", "John", 50, 54, 0.9)

        placeholder1 = mapper.get_placeholder(entity1)
        placeholder2 = mapper.get_placeholder(entity2)

        assert placeholder1 == placeholder2 == "<PERSON_1>"

    def test_different_types_separate_counters(self) -> None:
        """Test that different entity types have separate counters."""
        mapper = PlaceholderMapper()

        person = PIIEntity("PERSON", "John", 0, 4, 0.9)
        email = PIIEntity("EMAIL_ADDRESS", "john@test.com", 10, 23, 0.9)

        placeholder1 = mapper.get_placeholder(person)
        placeholder2 = mapper.get_placeholder(email)

        assert placeholder1 == "<PERSON_1>"
        assert placeholder2 == "<EMAIL_ADDRESS_1>"

    def test_get_mappings(self) -> None:
        """Test retrieving all mappings with entity details."""
        mapper = PlaceholderMapper()

        entity1 = PIIEntity("PERSON", "John", 0, 4, 0.9)
        entity2 = PIIEntity("EMAIL_ADDRESS", "john@test.com", 10, 23, 0.9)

        mapper.get_placeholder(entity1)
        mapper.get_placeholder(entity2)

        mappings = mapper.get_mappings()

        assert mappings == {
            "<PERSON_1>": {"text": "John", "entity_type": "PERSON", "score": 0.9},
            "<EMAIL_ADDRESS_1>": {"text": "john@test.com", "entity_type": "EMAIL_ADDRESS", "score": 0.9},
        }

    def test_reset_clears_state(self) -> None:
        """Test that reset clears all state."""
        mapper = PlaceholderMapper()

        entity = PIIEntity("PERSON", "John", 0, 4, 0.9)
        mapper.get_placeholder(entity)

        mapper.reset()

        assert mapper.get_mappings() == {}
        assert mapper.get_placeholder(entity) == "<PERSON_1>"


class TestAnonymizeTextWithMapping:
    """Tests for anonymize_text_with_mapping function."""

    def test_replaces_entities(self) -> None:
        """Test that entities are replaced with placeholders."""
        text = "Hello John, your email is john@test.com"
        entities = [
            PIIEntity("PERSON", "John", 6, 10, 0.9),
            PIIEntity("EMAIL_ADDRESS", "john@test.com", 26, 39, 0.9),
        ]
        mapper = PlaceholderMapper()

        result, mappings = anonymize_text_with_mapping(text, entities, mapper)

        assert result == "Hello <PERSON_1>, your email is <EMAIL_ADDRESS_1>"
        assert mappings == {
            "<PERSON_1>": {"text": "John", "entity_type": "PERSON", "score": 0.9},
            "<EMAIL_ADDRESS_1>": {"text": "john@test.com", "entity_type": "EMAIL_ADDRESS", "score": 0.9},
        }

    def test_handles_empty_entities(self) -> None:
        """Test handling text with no entities."""
        text = "Hello world"
        entities: list[PIIEntity] = []
        mapper = PlaceholderMapper()

        result, mappings = anonymize_text_with_mapping(text, entities, mapper)

        assert result == "Hello world"
        assert mappings == {}


class TestMappingFileFunctions:
    """Tests for mapping file save/load functions."""

    def test_save_and_load_mapping(self) -> None:
        """Test saving and loading mapping files."""
        mapping = {
            "<PERSON_1>": {"text": "John", "entity_type": "PERSON", "score": 0.9},
            "<EMAIL_1>": {"text": "john@test.com", "entity_type": "EMAIL_ADDRESS", "score": 1.0},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"

            save_mapping_to_file(
                mapping=mapping,
                output_path=path,
                document_name="test.txt",
                language="en",
                min_confidence_score=0.7,
            )

            assert path.exists()

            loaded = load_mapping_from_file(path)
            assert loaded == mapping

    def test_save_creates_parent_dirs(self) -> None:
        """Test that save creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "mapping.json"

            save_mapping_to_file(
                mapping={"<PERSON_1>": {"text": "John", "entity_type": "PERSON", "score": 0.9}},
                output_path=path,
                document_name="test.txt",
                language="en",
                min_confidence_score=0.7,
            )

            assert path.exists()

    def test_save_includes_metadata(self) -> None:
        """Test that saved file includes metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mapping.json"

            mapping = {"<PERSON_1>": {"text": "John", "entity_type": "PERSON", "score": 0.85}}
            save_mapping_to_file(
                mapping=mapping,
                output_path=path,
                document_name="test.txt",
                language="es",
                min_confidence_score=0.7,
            )

            with open(path) as f:
                data = json.load(f)

            assert data["document"] == "test.txt"
            assert data["language"] == "es"
            assert data["min_confidence_score"] == 0.7
            assert "timestamp" in data
            assert data["mappings"] == mapping
