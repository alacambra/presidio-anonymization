# Functional Requirements - Document Anonymization System

## Document Control

**Version**: 1.0
**Date**: 2025-11-25
**Status**: Active
**Project**: Presidio Document Anonymization System

---

## Functional Requirements

**REQ-F-001**: The system SHALL detect PII entities in text content including: PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IBAN_CODE, LOCATION, DATE_TIME, and NRP (national ID numbers).

**REQ-F-002**: The system SHALL anonymize detected PII by replacing it with indexed placeholders in the format `<TYPE_N>` (e.g., `<PERSON_1>`, `<EMAIL_1>`).

**REQ-F-003**: The system SHALL generate a mapping file (JSON) that maps each placeholder to its original value, enabling reversible anonymization.

**REQ-F-003.1**: The mapping file SHALL include: document name, timestamp, language, and placeholder-to-value mappings.

**REQ-F-004**: The system SHALL support processing plain text files (.txt).

**REQ-F-005**: The system SHALL support processing Word documents (.docx), preserving document structure (paragraphs, tables).

**REQ-F-006**: The system SHALL support processing PDF files (.pdf) by extracting text and generating a new PDF with anonymized content.

**REQ-F-007**: The system SHALL support multiple languages: English (en), Spanish (es), German (de), and Catalan (ca).

**REQ-F-008**: The system SHALL provide a command-line interface (CLI) for single file anonymization.

**REQ-F-009**: The system SHALL provide a CLI command for batch anonymization of all supported files in a directory.

**REQ-F-010**: The system SHALL provide a graphical user interface (GUI) for file selection and anonymization.

**REQ-F-010.1**: The GUI SHALL allow selection of input file or folder.

**REQ-F-010.2**: The GUI SHALL allow selection of output location.

**REQ-F-010.3**: The GUI SHALL allow selection of language.

**REQ-F-010.4**: The GUI SHALL display processing status and results.

**REQ-F-010.5**: The GUI SHALL provide access to view the generated mapping file.

**REQ-F-011**: The system SHALL ensure consistent placeholder assignment (same PII value receives same placeholder within a document).

---

## Architectural Requirements

**REQ-A-001**: The system SHALL follow hexagonal (ports & adapters) architecture separating core business logic from interface adapters.

**REQ-A-002**: The core anonymization service SHALL be independent of the interface layer (CLI/GUI), enabling both interfaces to use the same service methods.

**REQ-A-003**: Document handlers SHALL implement a common protocol/interface for consistent handling of different file formats.

**REQ-A-004**: The system SHALL use Microsoft Presidio for PII detection and anonymization.

**REQ-A-005**: The system SHALL use spaCy NLP models for language-specific entity recognition.

---

## Non-Functional Requirements

**REQ-NF-001**: The GUI SHALL be cross-platform compatible (macOS, Windows, Linux) using Tkinter.

**REQ-NF-002**: All public functions SHALL have complete type hints per Python typing standards.

**REQ-NF-003**: All public APIs SHALL have docstrings documenting purpose, arguments, and return values.

**REQ-NF-004**: The codebase SHALL have zero Pylance errors.

**REQ-NF-005**: Logging SHALL follow the format: `[method] message key=value;key=value`.

**REQ-NF-006**: Code SHALL use self-defining functions instead of inline comments.

**REQ-NF-007**: Package `__init__.py` files SHALL only export public API with `__all__`.

---

## Version History

| Version | Date       | Changes         | Author |
|---------|------------|-----------------|--------|
| 1.0     | 2025-11-25 | Initial version | Claude |
