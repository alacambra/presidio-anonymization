"""Handler for plain text files."""

from pathlib import Path
from typing import Tuple

from ..logger import setup_logger

logger = setup_logger(__name__)


class TxtHandler:
    """Handler for plain text (.txt) files."""

    @property
    def supported_extensions(self) -> Tuple[str, ...]:
        """Return supported file extensions."""
        return (".txt",)

    def read(self, path: Path) -> str:
        """
        Read text content from a .txt file.

        Args:
            path: Path to the text file

        Returns:
            Content of the text file
        """
        logger.info(f"reading text file path:{path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.info(f"text file read path:{path};length:{len(content)}")
        return content

    def write(self, path: Path, content: str) -> None:
        """
        Write content to a .txt file.

        Args:
            path: Path where to save the text file
            content: Text content to write
        """
        logger.info(f"writing text file path:{path}")

        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"text file written path:{path};length:{len(content)}")
