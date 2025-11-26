"""Tests for PDF document handler."""

import tempfile
from pathlib import Path

import fitz

from anonymizer.handlers.pdf_handler import PdfHandler


class TestPdfHandler:
    """Tests for PdfHandler class."""

    def test_supported_extensions(self) -> None:
        """Test that handler reports correct extensions."""
        handler = PdfHandler()
        assert handler.supported_extensions == (".pdf",)

    def test_read_file(self) -> None:
        """Test reading a pdf file."""
        handler = PdfHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.pdf"

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Hello World")
            page.insert_text((72, 100), "Line 2")
            doc.save(path)
            doc.close()

            content = handler.read(path)

            assert "Hello World" in content
            assert "Line 2" in content

    def test_write_file(self) -> None:
        """Test writing a pdf file."""
        handler = PdfHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.pdf"

            handler.write(path, "Test content\nLine 2")

            assert path.exists()

            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            assert "Test content" in text
            assert "Line 2" in text

    def test_write_creates_parent_dirs(self) -> None:
        """Test that write creates parent directories."""
        handler = PdfHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "output.pdf"

            handler.write(path, "Content")

            assert path.exists()

    def test_read_multipage(self) -> None:
        """Test reading multi-page pdf."""
        handler = PdfHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "multipage.pdf"

            doc = fitz.open()
            page1 = doc.new_page()
            page1.insert_text((72, 72), "Page 1 content")
            page2 = doc.new_page()
            page2.insert_text((72, 72), "Page 2 content")
            doc.save(path)
            doc.close()

            content = handler.read(path)

            assert "Page 1 content" in content
            assert "Page 2 content" in content

    def test_read_unicode(self) -> None:
        """Test reading file with unicode characters."""
        handler = PdfHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "unicode.pdf"

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "María García está en España")
            doc.save(path)
            doc.close()

            content = handler.read(path)

            assert "María" in content
            assert "España" in content

    def test_escape_xml_chars(self) -> None:
        """Test that XML special characters are escaped when writing."""
        handler = PdfHandler()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "special_chars.pdf"

            handler.write(path, "Test <PERSON_1> & <EMAIL_1>")

            assert path.exists()

            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            assert "<PERSON_1>" in text
            assert "<EMAIL_1>" in text
