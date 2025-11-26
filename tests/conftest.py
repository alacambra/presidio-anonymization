"""Pytest fixtures for anonymizer tests."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_text() -> str:
    """Return sample text containing PII for testing."""
    return (
        "John Smith can be reached at john.smith@email.com or 555-123-4567. "
        "His credit card number is 4111-1111-1111-1111. "
        "He lives in New York and was born on January 15, 1985."
    )


@pytest.fixture
def sample_text_spanish() -> str:
    """Return sample Spanish text containing PII for testing."""
    return (
        "María García puede ser contactada en maria.garcia@correo.com o 612-345-678. "
        "Su número de tarjeta es 4111-1111-1111-1111. "
        "Vive en Madrid y nació el 15 de enero de 1985."
    )
