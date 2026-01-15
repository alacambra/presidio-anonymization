"""Document handler protocol definition."""

from pathlib import Path
from typing import Protocol, Tuple


class DocumentHandler(Protocol):
    """
    Protocol for document handlers.

    All document handlers must implement read and write methods
    for their respective file formats.
    """

    @property
    def supported_extensions(self) -> Tuple[str, ...]:
        """
        Return supported file extensions.

        Returns:
            Tuple of supported extensions (e.g., ('.txt',))
        """
        ...

    def read(self, path: Path) -> str:
        """
        Extract text content from a document.

        Args:
            path: Path to the document file

        Returns:
            Extracted text content
        """
        ...

    def write(self, path: Path, content: str) -> None:
        """
        Write anonymized content to a document.

        Args:
            path: Path where to save the document
            content: Anonymized text content
        """
        ...
