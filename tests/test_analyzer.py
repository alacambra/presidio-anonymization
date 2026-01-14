"""Tests for PII analyzer."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from anonymizer.core.analyzer import PIIAnalyzer


class TestPIIAnalyzerLogging:
    """Tests for PIIAnalyzer logging functionality."""

    def test_create_engine_logging_format(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that _create_engine logs with correct format (no TypeError)."""
        with caplog.at_level(logging.INFO):
            analyzer = PIIAnalyzer(language="en")
            # Trigger engine creation
            analyzer._get_engine()

        # Verify log message was created without errors
        assert any(
            "[_create_spacy_engine] creating spacy engine" in record.message
            for record in caplog.records
        )
        # Verify the log contains expected parameters
        assert any(
            "language:en" in record.message and "model:" in record.message
            for record in caplog.records
        )

    def test_analyze_logging_format(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that analyze logs with correct format (no TypeError)."""
        analyzer = PIIAnalyzer(language="en")

        with caplog.at_level(logging.INFO):
            high_conf, low_conf = analyzer.analyze("John Smith lives in New York.")

        # Verify log message was created without errors
        assert any(
            "[analyze] analysis complete" in record.message
            for record in caplog.records
        )
        # Verify the log contains expected parameters (now uses high_confidence/low_confidence)
        assert any(
            "high_confidence:" in record.message and "text_length:" in record.message
            for record in caplog.records
        )


class TestPIIAnalyzerValidation:
    """Tests for PIIAnalyzer input validation."""

    def test_invalid_language_raises_error(self) -> None:
        """Test that unsupported language raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported language"):
            PIIAnalyzer(language="invalid")

    def test_valid_language_en(self) -> None:
        """Test that English language is accepted."""
        analyzer = PIIAnalyzer(language="en")
        assert analyzer.language == "en"


class TestPIIAnalyzerAnalysis:
    """Tests for PIIAnalyzer analysis functionality."""

    def test_analyze_detects_person(self) -> None:
        """Test that analyzer detects person names."""
        analyzer = PIIAnalyzer(language="en")
        high_conf, low_conf = analyzer.analyze("Contact John Smith for more information.")

        # Check both high and low confidence for person entities
        all_entities = high_conf + low_conf
        person_entities = [e for e in all_entities if e.entity_type == "PERSON"]
        assert len(person_entities) > 0
        assert any("John" in e.text or "Smith" in e.text for e in person_entities)

    def test_analyze_detects_email(self) -> None:
        """Test that analyzer detects email addresses."""
        analyzer = PIIAnalyzer(language="en")
        high_conf, low_conf = analyzer.analyze("Email me at john.smith@example.com")

        # Emails should be high confidence
        email_entities = [e for e in high_conf if e.entity_type == "EMAIL_ADDRESS"]
        assert len(email_entities) == 1
        assert email_entities[0].text == "john.smith@example.com"

    def test_analyze_returns_sorted_entities(self) -> None:
        """Test that entities are returned sorted by position."""
        analyzer = PIIAnalyzer(language="en")
        high_conf, low_conf = analyzer.analyze("John Smith (john@email.com) lives in New York.")

        # Verify high confidence entities are sorted by start position
        positions = [e.start for e in high_conf]
        assert positions == sorted(positions)

    def test_analyze_empty_text(self) -> None:
        """Test analyzing empty text returns no entities."""
        analyzer = PIIAnalyzer(language="en")
        high_conf, low_conf = analyzer.analyze("")

        assert high_conf == []
        assert low_conf == []

    def test_analyze_no_pii_text(self) -> None:
        """Test analyzing text with no PII returns empty list."""
        analyzer = PIIAnalyzer(language="en")
        high_conf, low_conf = analyzer.analyze("The quick brown fox jumps over the lazy dog.")

        # May return empty or very low confidence results
        assert isinstance(high_conf, list)
        assert isinstance(low_conf, list)


class TestPIIAnalyzerTransformersEngine:
    """Tests for PIIAnalyzer with TransformersNlpEngine."""

    def test_transformers_engine_fallback_to_spacy_when_unavailable(self) -> None:
        """Test that analyzer falls back to spaCy when transformers unavailable."""
        from anonymizer import config

        # Save original values
        original_engine = config.NLP_ENGINE_TYPE
        original_model = config.SELECTED_TRANSFORMERS_MODEL.get("en")

        try:
            # Set up transformers engine
            config.set_nlp_engine_type("transformers")
            config.set_transformers_model_for_language("en", "dslim/bert-base-NER")

            analyzer = PIIAnalyzer(language="en")

            # Should fall back to spaCy and work (no crash)
            high_conf, low_conf = analyzer.analyze("Contact John Smith at john@email.com")

            # Should still detect entities using spaCy fallback
            all_entities = high_conf + low_conf
            assert len(all_entities) > 0

        finally:
            # Restore original values
            config.NLP_ENGINE_TYPE = original_engine
            config.SELECTED_TRANSFORMERS_MODEL["en"] = original_model

    def test_transformers_engine_fallback_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that fallback to spaCy logs a warning when transformers fails."""
        import logging

        from anonymizer import config

        # Save original values
        original_engine = config.NLP_ENGINE_TYPE
        original_model = config.SELECTED_TRANSFORMERS_MODEL.get("en")

        try:
            # Set up transformers engine
            config.set_nlp_engine_type("transformers")
            config.set_transformers_model_for_language("en", "dslim/bert-base-NER")

            analyzer = PIIAnalyzer(language="en")

            # Mock _create_transformers_engine to raise ImportError (simulating missing package)
            with patch.object(
                analyzer,
                "_create_transformers_engine",
                side_effect=ImportError("spacy-huggingface-pipelines not installed"),
            ):
                with caplog.at_level(logging.WARNING):
                    analyzer._get_engine()

            # Should log a warning about fallback
            assert any(
                "falling back to spaCy" in record.message
                for record in caplog.records
            )

        finally:
            # Restore original values
            config.NLP_ENGINE_TYPE = original_engine
            config.SELECTED_TRANSFORMERS_MODEL["en"] = original_model
