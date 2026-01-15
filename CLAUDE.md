# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cross-platform document anonymization tool using Microsoft Presidio for PII detection. Supports txt, md, docx, and pdf files with multi-language support (English, Spanish, German, Catalan).

## Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run tests
pytest

# Run a single test
pytest tests/test_analyzer.py::test_function_name -v

# Run CLI
anonymize file <input-file> -o <output-file> -l en -t 0.7

# Run GUI
anonymize-gui

# Type checking (pyright configured in pyproject.toml)
pyright src/
```

## Architecture

Hexagonal architecture with clear separation between core logic and interfaces.

### Layer Structure

```
src/anonymizer/
├── core/           # Business logic (no external dependencies)
│   ├── analyzer.py         # PIIAnalyzer - Presidio wrapper for PII detection
│   ├── anonymizer_service.py  # Main service - orchestrates analysis + mapping
│   ├── mapping.py          # PlaceholderMapper - consistent placeholder generation
│   └── models.py           # Domain models (PIIEntity, AnonymizationResult)
├── handlers/       # Document format adapters
│   ├── base.py             # DocumentHandler protocol
│   ├── txt_handler.py      # Plain text (.txt, .md)
│   ├── docx_handler.py     # Word documents
│   └── pdf_handler.py      # PDF documents
├── ports/          # Interface adapters
│   ├── cli.py              # Typer-based CLI
│   └── gui/                # Tkinter MVP GUI
│       ├── app.py          # Composition root
│       ├── views/          # Tkinter windows/dialogs (no business logic)
│       └── presenters/     # Handle user actions, call services
└── config.py       # Configuration (languages, models, entities)
```

### Key Patterns

1. **Service Layer**: `AnonymizerService` is the single entry point for both CLI and GUI. Never call `PIIAnalyzer` or `PlaceholderMapper` directly from interfaces.

2. **Document Handlers**: All handlers implement `DocumentHandler` protocol with `read()` and `write()` methods. Factory function `get_handler(extension)` returns the correct handler.

3. **GUI MVP Pattern**: Views are pure Tkinter with callbacks. Presenters receive view events and call services. Composition root in `app.py` wires dependencies.

4. **Lazy Initialization**: Both `AnonymizerService` and `PIIAnalyzer` lazily initialize NLP models on first use to reduce startup time.

### NLP Engine Configuration

The system supports two NLP backends configured globally in `config.py`:
- **spaCy** (default): Uses language-specific spaCy models (sm/md/lg/trf variants)
- **Transformers**: Uses HuggingFace models via `spacy-huggingface-pipelines`

Model selection functions: `set_model_for_language()`, `set_nlp_engine_type()`, `set_transformers_model_for_language()`

## Entity Types

Supported PII types (defined in `config.SUPPORTED_ENTITIES`):
- PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IBAN_CODE, LOCATION, DATE_TIME, NRP

## Output Files

Anonymization produces three files:
- `{name}.anonym.{ext}` - Anonymized document
- `{name}.anonym_mapping.json` - Placeholder-to-value mappings (for reversal)
- `{name}.anonym_excluded_entities.json` - Entities below threshold or user-deselected

## Coding Conventions

- Logging format: `logger.info(f"[method] message key:{value};key:{value}")`
- All public APIs require type hints and docstrings
- Package `__init__.py` exports only public API via `__all__`
