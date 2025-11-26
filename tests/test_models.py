"""Tests for core models."""

from anonymizer.core.models import AnonymizationResult, DocumentResult, PIIEntity


class TestPIIEntity:
    """Tests for PIIEntity dataclass."""

    def test_create_pii_entity(self) -> None:
        """Test creating a PIIEntity instance."""
        entity = PIIEntity(
            entity_type="PERSON",
            text="John Smith",
            start=0,
            end=10,
            score=0.95,
        )

        assert entity.entity_type == "PERSON"
        assert entity.text == "John Smith"
        assert entity.start == 0
        assert entity.end == 10
        assert entity.score == 0.95


class TestAnonymizationResult:
    """Tests for AnonymizationResult dataclass."""

    def test_create_result_with_defaults(self) -> None:
        """Test creating result with default empty collections."""
        result = AnonymizationResult(
            original_text="Hello John",
            anonymized_text="Hello <PERSON_1>",
        )

        assert result.original_text == "Hello John"
        assert result.anonymized_text == "Hello <PERSON_1>"
        assert result.mappings == {}
        assert result.entities_found == []

    def test_create_result_with_mappings(self) -> None:
        """Test creating result with mappings and entities."""
        entity = PIIEntity("PERSON", "John", 6, 10, 0.9)

        result = AnonymizationResult(
            original_text="Hello John",
            anonymized_text="Hello <PERSON_1>",
            mappings={"<PERSON_1>": "John"},
            entities_found=[entity],
        )

        assert result.mappings == {"<PERSON_1>": "John"}
        assert len(result.entities_found) == 1


class TestDocumentResult:
    """Tests for DocumentResult dataclass."""

    def test_create_document_result(self) -> None:
        """Test creating a DocumentResult instance."""
        result = DocumentResult(
            input_path="/input/doc.txt",
            output_path="/output/doc_anonymized.txt",
            mapping_path="/output/doc_anonymized_mapping.json",
            language="en",
            entities_count=5,
        )

        assert result.input_path == "/input/doc.txt"
        assert result.output_path == "/output/doc_anonymized.txt"
        assert result.mapping_path == "/output/doc_anonymized_mapping.json"
        assert result.language == "en"
        assert result.entities_count == 5
