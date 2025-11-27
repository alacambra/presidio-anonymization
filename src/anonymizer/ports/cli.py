"""CLI interface using Typer."""

from pathlib import Path
from typing import Optional

import typer

from ..config import DEFAULT_LANGUAGE, SUPPORTED_FILE_EXTENSIONS, SUPPORTED_LANGUAGES
from ..core.anonymizer_service import AnonymizerService

app = typer.Typer(
    name="anonymize",
    help="Document anonymization tool using Microsoft Presidio",
    add_completion=False,
)


def validate_language(language: str) -> str:
    """Validate language code callback."""
    if language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(SUPPORTED_LANGUAGES.keys())
        raise typer.BadParameter(f"Unsupported language. Choose from: {supported}")
    return language


@app.command("file")
def anonymize_file(
    input_path: Path = typer.Argument(
        ...,
        help="Path to the document to anonymize",
        exists=True,
        readable=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output",
        help="Output path for anonymized document",
    ),
    language: str = typer.Option(
        DEFAULT_LANGUAGE,
        "-l",
        "--language",
        help="Language for PII detection (en, es, de, ca)",
        callback=validate_language,
    ),
    threshold: float = typer.Option(
        0.7,
        "-t",
        "--threshold",
        help="Minimum confidence threshold (0.0-1.0)",
        min=0.0,
        max=1.0,
    ),
    auto_select: bool = typer.Option(
        True,
        "--auto-select/--no-auto-select",
        help="Automatically select all entities above threshold (non-interactive mode)",
    ),
) -> None:
    """
    Anonymize a single document.

    Supports .txt, .md, .docx, and .pdf files.
    In auto-select mode (default), all entities above the threshold are automatically anonymized.
    """
    typer.echo(f"Anonymizing: {input_path}")
    typer.echo(f"Language: {language}")
    typer.echo(f"Confidence threshold: {threshold}")

    service = AnonymizerService(language=language, min_confidence=threshold)

    # CLI uses auto-select (no interactive dialog)
    result = service.anonymize_file_with_selection(
        input_path,
        output,
        selection_callback=None if auto_select else None  # None means use all detected
    )

    if result is None:
        typer.echo(typer.style("Anonymization cancelled.", fg=typer.colors.YELLOW))
        raise typer.Exit(1)

    typer.echo("")
    typer.echo(typer.style("Anonymization complete!", fg=typer.colors.GREEN, bold=True))
    typer.echo(f"  Output: {result.output_path}")
    typer.echo(f"  Mapping: {result.mapping_path}")
    typer.echo(f"  Entities anonymized: {result.entities_count}")


@app.command("languages")
def list_languages() -> None:
    """List supported languages."""
    typer.echo("Supported languages:")
    for code, model in SUPPORTED_LANGUAGES.items():
        typer.echo(f"  {code}: {model}")


@app.command("formats")
def list_formats() -> None:
    """List supported file formats."""
    typer.echo("Supported file formats:")
    for ext in SUPPORTED_FILE_EXTENSIONS:
        typer.echo(f"  {ext}")


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
