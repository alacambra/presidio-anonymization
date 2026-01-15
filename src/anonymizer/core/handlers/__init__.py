"""Document handlers for different file formats."""

from .base import DocumentHandler
from .txt_handler import TxtHandler
from .docx_handler import DocxHandler
from .pdf_handler import PdfHandler

__all__ = [
    "DocumentHandler",
    "TxtHandler",
    "DocxHandler",
    "PdfHandler",
]


def get_handler(file_extension: str) -> DocumentHandler:
    """
    Get the appropriate handler for a file extension.

    Args:
        file_extension: File extension including dot (e.g., '.txt')

    Returns:
        DocumentHandler instance for the file type

    Raises:
        ValueError: If file type is not supported
    """
    handlers: dict[str, type[DocumentHandler]] = {
        ".txt": TxtHandler,
        ".md": TxtHandler,
        ".docx": DocxHandler,
        ".pdf": PdfHandler,
    }

    ext = file_extension.lower()
    if ext not in handlers:
        supported = ", ".join(handlers.keys())
        raise ValueError(
            f"Unsupported file type: {ext}. Supported types: {supported}"
        )

    return handlers[ext]()
