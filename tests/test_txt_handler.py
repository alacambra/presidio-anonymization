"""Tests for TXT document handler."""

import tempfile
from pathlib import Path

from anonymizer.handlers.txt_handler import TxtHandler


class TestTxtHandler:
    """Tests for TxtHandler class."""

    def test_supported_extensions(self) -> None:
        """Test that handler reports correct extensions."""
        handler = TxtHandler()
        assert handler.supported_extensions == (".txt",)

    def test_read_file(self) -> None:
        """Test reading a text file."""
        handler = TxtHandler()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Hello World\nLine 2")
            temp_path = Path(f.name)

        try:
            content = handler.read(temp_path)
            assert content == "Hello World\nLine 2"
        finally:
            temp_path.unlink()

    def test_write_file(self) -> None:
        """Test writing a text file."""
        handler = TxtHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.txt"

            handler.write(path, "Test content\nLine 2")

            assert path.exists()
            assert path.read_text(encoding="utf-8") == "Test content\nLine 2"

    def test_write_creates_parent_dirs(self) -> None:
        """Test that write creates parent directories."""
        handler = TxtHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "output.txt"

            handler.write(path, "Content")

            assert path.exists()

    def test_read_unicode(self) -> None:
        """Test reading file with unicode characters."""
        handler = TxtHandler()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("María García está en España")
            temp_path = Path(f.name)

        try:
            content = handler.read(temp_path)
            assert "María García" in content
            assert "España" in content
        finally:
            temp_path.unlink()
