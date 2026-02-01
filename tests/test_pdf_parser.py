"""Tests for PDFParser module."""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.core.pdf_parser import (
    PDFParser, PDFPage, TextChunk, PDFExtractionResult, PYPDF_AVAILABLE,
)


class TestDataclasses(unittest.TestCase):
    """Test dataclass construction and defaults."""

    def test_pdf_page(self):
        page = PDFPage(page_number=1, text="Hello world", source_file="/tmp/test.pdf")
        self.assertEqual(page.page_number, 1)
        self.assertEqual(page.text, "Hello world")
        self.assertEqual(page.source_file, "/tmp/test.pdf")

    def test_text_chunk(self):
        chunk = TextChunk(
            text="chunk text", chunk_index=0,
            source_file="/tmp/test.pdf", start_page=1, end_page=2,
        )
        self.assertEqual(chunk.chunk_index, 0)
        self.assertEqual(chunk.start_page, 1)
        self.assertEqual(chunk.end_page, 2)

    def test_pdf_extraction_result_defaults(self):
        result = PDFExtractionResult()
        self.assertEqual(result.pages, [])
        self.assertEqual(result.source_files, [])
        self.assertEqual(result.total_chars, 0)
        self.assertEqual(result.errors, [])


class TestPDFParserAvailability(unittest.TestCase):
    """Test is_available() reflects pypdf import status."""

    def test_is_available_matches_constant(self):
        self.assertEqual(PDFParser.is_available(), PYPDF_AVAILABLE)


class TestChunking(unittest.TestCase):
    """Test chunk_text logic (no pypdf needed)."""

    def setUp(self):
        self.parser = PDFParser(chunk_size=100, chunk_overlap=20)

    def test_empty_pages_returns_empty(self):
        self.assertEqual(self.parser.chunk_text([]), [])

    def test_single_short_page_single_chunk(self):
        pages = [PDFPage(page_number=1, text="Short text.", source_file="a.pdf")]
        chunks = self.parser.chunk_text(pages)
        self.assertEqual(len(chunks), 1)
        self.assertIn("Short text.", chunks[0].text)
        self.assertEqual(chunks[0].start_page, 1)
        self.assertEqual(chunks[0].end_page, 1)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[0].source_file, "a.pdf")

    def test_long_text_produces_multiple_chunks(self):
        # 300 chars of text with chunk_size=100 should produce multiple chunks
        long_text = "Word " * 60  # ~300 chars
        pages = [PDFPage(page_number=1, text=long_text, source_file="a.pdf")]
        chunks = self.parser.chunk_text(pages)
        self.assertGreater(len(chunks), 1)
        # All chunks should have valid indexes
        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk.chunk_index, i)

    def test_multiple_pages_tracked_correctly(self):
        pages = [
            PDFPage(page_number=1, text="Page one content.", source_file="a.pdf"),
            PDFPage(page_number=2, text="Page two content.", source_file="a.pdf"),
        ]
        # With a large chunk_size, both pages fit in one chunk
        parser = PDFParser(chunk_size=5000, chunk_overlap=0)
        chunks = parser.chunk_text(pages)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].start_page, 1)
        self.assertEqual(chunks[0].end_page, 2)

    def test_whitespace_only_pages_skipped(self):
        pages = [PDFPage(page_number=1, text="   \n\n  ", source_file="a.pdf")]
        chunks = self.parser.chunk_text(pages)
        self.assertEqual(len(chunks), 0)


class TestGetTextForPrompt(unittest.TestCase):
    """Test prompt text formatting."""

    def setUp(self):
        self.parser = PDFParser(max_prompt_text_size=500)

    def test_empty_result_returns_empty(self):
        result = PDFExtractionResult()
        self.assertEqual(self.parser.get_text_for_prompt(result), "")

    def test_formats_pages_with_headers(self):
        result = PDFExtractionResult(
            pages=[
                PDFPage(page_number=1, text="First page text", source_file="/tmp/resume.pdf"),
                PDFPage(page_number=2, text="Second page text", source_file="/tmp/resume.pdf"),
            ],
            source_files=["/tmp/resume.pdf"],
            total_chars=30,
        )
        text = self.parser.get_text_for_prompt(result)
        self.assertIn("=== File: resume.pdf ===", text)
        self.assertIn("--- Page 1 ---", text)
        self.assertIn("First page text", text)
        self.assertIn("--- Page 2 ---", text)
        self.assertIn("Second page text", text)

    def test_multiple_source_files_get_headers(self):
        result = PDFExtractionResult(
            pages=[
                PDFPage(page_number=1, text="Resume", source_file="/tmp/resume.pdf"),
                PDFPage(page_number=1, text="LinkedIn", source_file="/tmp/linkedin.pdf"),
            ],
            source_files=["/tmp/resume.pdf", "/tmp/linkedin.pdf"],
            total_chars=15,
        )
        text = self.parser.get_text_for_prompt(result)
        self.assertIn("=== File: resume.pdf ===", text)
        self.assertIn("=== File: linkedin.pdf ===", text)

    def test_truncation_when_over_limit(self):
        long_text = "A" * 600
        result = PDFExtractionResult(
            pages=[PDFPage(page_number=1, text=long_text, source_file="/tmp/big.pdf")],
            source_files=["/tmp/big.pdf"],
            total_chars=600,
        )
        text = self.parser.get_text_for_prompt(result)
        self.assertIn("[... truncated due to length ...]", text)
        # Total should be under max + some overhead for the truncation marker
        self.assertLess(len(text), 600)


class TestExtractPages(unittest.TestCase):
    """Test extract_pages with mocked pypdf."""

    def test_file_not_found(self):
        parser = PDFParser()
        if not PYPDF_AVAILABLE:
            result = parser.extract_pages("/nonexistent/file.pdf")
            self.assertGreater(len(result.errors), 0)
            return
        result = parser.extract_pages("/nonexistent/file.pdf")
        self.assertGreater(len(result.errors), 0)
        self.assertEqual(len(result.pages), 0)

    @unittest.skipUnless(PYPDF_AVAILABLE, "pypdf not installed")
    def test_extract_with_mock_reader(self):
        """Test extraction by mocking PdfReader."""
        parser = PDFParser()

        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page one content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page two content"

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]

        with patch("src.core.pdf_parser.PdfReader", return_value=mock_reader):
            # Create a temp file so the path exists
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                temp_path = f.name

            try:
                result = parser.extract_pages(temp_path)
                self.assertEqual(len(result.pages), 2)
                self.assertEqual(result.pages[0].text, "Page one content")
                self.assertEqual(result.pages[1].text, "Page two content")
                self.assertEqual(result.pages[0].page_number, 1)
                self.assertEqual(result.pages[1].page_number, 2)
                self.assertEqual(result.total_chars, len("Page one content") + len("Page two content"))
            finally:
                Path(temp_path).unlink(missing_ok=True)


class TestExtractFromDirectory(unittest.TestCase):
    """Test directory extraction."""

    def test_nonexistent_directory(self):
        parser = PDFParser()
        result = parser.extract_from_directory("/nonexistent/dir/")
        self.assertGreater(len(result.errors), 0)

    def test_empty_directory(self):
        parser = PDFParser()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = parser.extract_from_directory(tmpdir)
            self.assertGreater(len(result.errors), 0)
            self.assertIn("No files matching", result.errors[0])

    @unittest.skipUnless(PYPDF_AVAILABLE, "pypdf not installed")
    def test_directory_with_mocked_pdfs(self):
        """Test directory extraction with mocked PdfReader."""
        parser = PDFParser()

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted content"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake PDF files
            (Path(tmpdir) / "resume.pdf").write_bytes(b"%PDF-fake")
            (Path(tmpdir) / "linkedin.pdf").write_bytes(b"%PDF-fake")
            # Non-PDF should be ignored
            (Path(tmpdir) / "notes.txt").write_text("not a pdf")

            with patch("src.core.pdf_parser.PdfReader", return_value=mock_reader):
                result = parser.extract_from_directory(tmpdir)
                self.assertEqual(len(result.source_files), 2)
                self.assertEqual(len(result.pages), 2)  # one page per PDF


class TestMergedPromptGeneration(unittest.TestCase):
    """Test that extracted text integrates correctly with prompt generation."""

    def test_prompt_with_extracted_text(self):
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.core.job_search_mvp import JobSearchMVP
        mvp = JobSearchMVP()

        extracted = "John Doe\nSoftware Engineer\njohn@example.com"
        prompt = mvp.generate_resume_parse_prompt(extracted_text=extracted)

        self.assertIn("=== EXTRACTED RESUME TEXT ===", prompt)
        self.assertIn("John Doe", prompt)
        self.assertIn("john@example.com", prompt)
        self.assertIn("profile_extracted.json", prompt)
        # Should NOT contain "Read these files"
        self.assertNotIn("Read these files", prompt)

    def test_prompt_without_extracted_text(self):
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.core.job_search_mvp import JobSearchMVP
        mvp = JobSearchMVP()

        prompt = mvp.generate_resume_parse_prompt()
        self.assertIn("Read these files", prompt)
        self.assertNotIn("=== EXTRACTED RESUME TEXT ===", prompt)


class TestMergeParsedProfiles(unittest.TestCase):
    """Test ProfileManager.merge_parsed_profiles."""

    def test_empty_list(self):
        from src.core.profile_manager import ProfileManager
        merged = ProfileManager.merge_parsed_profiles([])
        self.assertIn("personal_info", merged)

    def test_single_profile_returns_copy(self):
        from src.core.profile_manager import ProfileManager
        profile = ProfileManager().create_empty_profile()
        profile["personal_info"]["name"] = "Test"
        merged = ProfileManager.merge_parsed_profiles([profile])
        self.assertEqual(merged["personal_info"]["name"], "Test")

    def test_merges_skills_without_duplicates(self):
        from src.core.profile_manager import ProfileManager
        p1 = ProfileManager().create_empty_profile()
        p1["skills"]["technical"] = ["python", "java"]
        p2 = ProfileManager().create_empty_profile()
        p2["skills"]["technical"] = ["java", "go"]

        merged = ProfileManager.merge_parsed_profiles([p1, p2])
        self.assertEqual(sorted(merged["skills"]["technical"]), ["go", "java", "python"])

    def test_merges_personal_info_first_nonempty(self):
        from src.core.profile_manager import ProfileManager
        p1 = ProfileManager().create_empty_profile()
        p1["personal_info"]["email"] = "a@test.com"
        p2 = ProfileManager().create_empty_profile()
        p2["personal_info"]["email"] = "b@test.com"
        p2["personal_info"]["name"] = "Bob"

        merged = ProfileManager.merge_parsed_profiles([p1, p2])
        # First non-empty email wins
        self.assertEqual(merged["personal_info"]["email"], "a@test.com")
        # Name comes from p2 since p1 was empty
        self.assertEqual(merged["personal_info"]["name"], "Bob")

    def test_merges_experience_deduplicates(self):
        from src.core.profile_manager import ProfileManager
        p1 = ProfileManager().create_empty_profile()
        p1["experience"] = [{"title": "Engineer", "company": "A"}]
        p2 = ProfileManager().create_empty_profile()
        p2["experience"] = [
            {"title": "Engineer", "company": "A"},
            {"title": "Manager", "company": "B"},
        ]

        merged = ProfileManager.merge_parsed_profiles([p1, p2])
        titles = [e["title"] for e in merged["experience"]]
        self.assertEqual(len(titles), 2)
        self.assertIn("Engineer", titles)
        self.assertIn("Manager", titles)


if __name__ == "__main__":
    unittest.main()
