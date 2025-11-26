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
) -> None:
    """
    Anonymize a single document.

    Supports .txt, .docx, and .pdf files.
    """
    typer.echo(f"Anonymizing: {input_path}")
    typer.echo(f"Language: {language}")

    service = AnonymizerService(language=language)

    result = service.anonymize_file(input_path, output)

    typer.echo("")
    typer.echo(typer.style("Anonymization complete!", fg=typer.colors.GREEN, bold=True))
    typer.echo(f"  Output: {result.output_path}")
    typer.echo(f"  Mapping: {result.mapping_path}")
    typer.echo(f"  Entities found: {result.entities_count}")


@app.command("directory")
def anonymize_directory(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory containing documents to anonymize",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output_dir: Path = typer.Option(
        ...,
        "-o",
        "--output",
        help="Output directory for anonymized documents",
    ),
    language: str = typer.Option(
        DEFAULT_LANGUAGE,
        "-l",
        "--language",
        help="Language for PII detection (en, es, de, ca)",
        callback=validate_language,
    ),
) -> None:
    """
    Anonymize all supported documents in a directory.

    Processes .txt, .docx, and .pdf files recursively.
    """
    typer.echo(f"Anonymizing directory: {input_dir}")
    typer.echo(f"Output directory: {output_dir}")
    typer.echo(f"Language: {language}")
    typer.echo("")

    service = AnonymizerService(language=language)

    results = service.anonymize_directory(input_dir, output_dir)

    typer.echo("")
    typer.echo(
        typer.style(
            f"Anonymization complete! Processed {len(results)} files.",
            fg=typer.colors.GREEN,
            bold=True,
        )
    )

    total_entities = sum(r.entities_count for r in results)
    typer.echo(f"  Total entities anonymized: {total_entities}")

    for result in results:
        typer.echo(f"  - {result.input_path} -> {result.output_path}")


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
