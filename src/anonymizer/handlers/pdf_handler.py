"""Handler for PDF documents."""

from pathlib import Path
from typing import List, Tuple

import fitz  # type: ignore[import-untyped]  # PyMuPDF
from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer  # type: ignore[import-untyped]

from ..logger import setup_logger

logger = setup_logger(__name__)


class PdfHandler:
    """
    Handler for PDF documents.

    Extracts text from PDFs and creates new PDFs with anonymized content.
    Note: Original formatting is not preserved when writing.
    """

    @property
    def supported_extensions(self) -> Tuple[str, ...]:
        """Return supported file extensions."""
        return (".pdf",)

    def read(self, path: Path) -> str:
        """
        Extract text from a PDF document.

        Args:
            path: Path to the PDF file

        Returns:
            Extracted text content
        """
        logger.info(f"reading pdf file path:{path}")

        doc = fitz.open(path)
        text_parts: List[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(page_text)

        doc.close()

        content = "\n\n".join(text_parts)

        logger.info(f"pdf file read path:{path};length:{len(content)}")
        return content

    def write(self, path: Path, content: str) -> None:
        """
        Write anonymized content to a new PDF.

        Creates a simple text-based PDF. Original formatting is not preserved.

        Args:
            path: Path where to save the PDF file
            content: Anonymized text content
        """
        logger.info(f"writing pdf file path:{path}")

        path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        styles = getSampleStyleSheet()
        story = self._create_story(content, styles)

        doc.build(story)

        logger.info(f"pdf file written path:{path}")

    def _create_story(
        self, content: str, styles: ParagraphStyle
    ) -> List[Paragraph | Spacer]:
        """Create the PDF story (list of flowables)."""
        story: List[Paragraph | Spacer] = []
        paragraphs = content.split("\n")

        for paragraph_text in paragraphs:
            if paragraph_text.strip():
                clean_text = self._escape_xml_chars(paragraph_text)
                para = Paragraph(clean_text, styles["Normal"])
                story.append(para)
                story.append(Spacer(1, 12))

        return story

    def _escape_xml_chars(self, text: str) -> str:
        """Escape XML special characters for ReportLab."""
        replacements = [
            ("&", "&amp;"),
            ("<", "&lt;"),
            (">", "&gt;"),
        ]

        result = text
        for old, new in replacements:
            result = result.replace(old, new)

        return result
