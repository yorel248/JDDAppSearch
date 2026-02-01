"""PDF Parser for extracting text from resume PDFs with configurable chunking."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


@dataclass
class PDFPage:
    """Represents a single page extracted from a PDF."""
    page_number: int
    text: str
    source_file: str


@dataclass
class TextChunk:
    """A chunk of text with metadata for prompt embedding."""
    text: str
    chunk_index: int
    source_file: str
    start_page: int
    end_page: int


@dataclass
class PDFExtractionResult:
    """Result of extracting text from one or more PDFs."""
    pages: List[PDFPage] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    total_chars: int = 0
    errors: List[str] = field(default_factory=list)


class PDFParser:
    """Extracts text from PDFs page-by-page with configurable chunking."""

    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 200,
                 max_prompt_text_size: int = 50000):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_prompt_text_size = max_prompt_text_size

    @staticmethod
    def is_available() -> bool:
        """Check if pypdf is installed."""
        return PYPDF_AVAILABLE

    def extract_pages(self, pdf_path: str) -> PDFExtractionResult:
        """Extract text page-by-page from a single PDF.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            PDFExtractionResult with pages and metadata.
        """
        result = PDFExtractionResult()
        pdf_path = str(pdf_path)
        result.source_files.append(pdf_path)

        if not PYPDF_AVAILABLE:
            result.errors.append("pypdf is not installed. Install with: pip install pypdf")
            return result

        path = Path(pdf_path)
        if not path.exists():
            result.errors.append(f"File not found: {pdf_path}")
            return result

        try:
            reader = PdfReader(pdf_path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pdf_page = PDFPage(
                        page_number=i + 1,
                        text=text,
                        source_file=pdf_path,
                    )
                    result.pages.append(pdf_page)
                    result.total_chars += len(text)
        except Exception as e:
            result.errors.append(f"Error reading {pdf_path}: {e}")

        return result

    def extract_from_directory(self, directory: str,
                               pattern: str = "*.pdf") -> PDFExtractionResult:
        """Extract text from all matching PDFs in a directory.

        Args:
            directory: Directory path to scan.
            pattern: Glob pattern for PDF files.

        Returns:
            Combined PDFExtractionResult from all matched files.
        """
        combined = PDFExtractionResult()
        dir_path = Path(directory)

        if not dir_path.is_dir():
            combined.errors.append(f"Directory not found: {directory}")
            return combined

        pdf_files = sorted(dir_path.glob(pattern))
        if not pdf_files:
            combined.errors.append(f"No files matching '{pattern}' in {directory}")
            return combined

        for pdf_file in pdf_files:
            file_result = self.extract_pages(str(pdf_file))
            combined.pages.extend(file_result.pages)
            combined.source_files.extend(file_result.source_files)
            combined.total_chars += file_result.total_chars
            combined.errors.extend(file_result.errors)

        return combined

    def chunk_text(self, pages: List[PDFPage]) -> List[TextChunk]:
        """Split pages into size-aware chunks with overlap.

        Args:
            pages: List of PDFPage objects to chunk.

        Returns:
            List of TextChunk objects.
        """
        if not pages:
            return []

        # Concatenate all page texts with page markers
        segments = []
        for page in pages:
            segments.append((page.page_number, page.source_file, page.text))

        # Build a single string with page boundary tracking
        full_text = ""
        # Map: character offset -> (page_number, source_file)
        page_boundaries = []
        for page_num, source_file, text in segments:
            start_offset = len(full_text)
            full_text += text + "\n"
            page_boundaries.append((start_offset, len(full_text), page_num, source_file))

        if not full_text.strip():
            return []

        chunks = []
        chunk_index = 0
        pos = 0

        while pos < len(full_text):
            end = min(pos + self.chunk_size, len(full_text))

            # Try to break at a paragraph or sentence boundary
            if end < len(full_text):
                # Look for paragraph break
                para_break = full_text.rfind("\n\n", pos, end)
                if para_break > pos + self.chunk_size // 2:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    for sep in (". ", ".\n", "\n"):
                        sent_break = full_text.rfind(sep, pos, end)
                        if sent_break > pos + self.chunk_size // 2:
                            end = sent_break + len(sep)
                            break

            chunk_text = full_text[pos:end].strip()
            if chunk_text:
                # Determine which pages this chunk spans
                start_page = self._page_at_offset(page_boundaries, pos)
                end_page = self._page_at_offset(page_boundaries, end - 1)
                source = self._source_at_offset(page_boundaries, pos)

                chunks.append(TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    source_file=source,
                    start_page=start_page,
                    end_page=end_page,
                ))
                chunk_index += 1

            # Advance with overlap
            pos = end - self.chunk_overlap if end < len(full_text) else end
            # Prevent infinite loop
            if pos <= (end - self.chunk_size) or pos <= 0:
                pos = end

        return chunks

    def get_text_for_prompt(self, result: PDFExtractionResult) -> str:
        """Format extracted text for embedding in a prompt.

        Concatenates page texts with headers, truncates if over max_prompt_text_size.

        Args:
            result: PDFExtractionResult to format.

        Returns:
            Formatted string ready for prompt embedding.
        """
        if not result.pages:
            return ""

        parts = []
        current_source = None

        for page in result.pages:
            if page.source_file != current_source:
                current_source = page.source_file
                filename = Path(page.source_file).name
                parts.append(f"\n=== File: {filename} ===\n")

            parts.append(f"--- Page {page.page_number} ---\n{page.text}\n")

        full_text = "\n".join(parts)

        if len(full_text) > self.max_prompt_text_size:
            truncated = full_text[:self.max_prompt_text_size]
            # Try to break at a sentence
            last_period = truncated.rfind(". ")
            if last_period > self.max_prompt_text_size * 0.8:
                truncated = truncated[:last_period + 1]
            full_text = truncated + "\n\n[... truncated due to length ...]"

        return full_text

    @staticmethod
    def _page_at_offset(boundaries, offset):
        """Find the page number at a given character offset."""
        for start, end, page_num, _ in boundaries:
            if start <= offset < end:
                return page_num
        # Fallback to last page
        return boundaries[-1][2] if boundaries else 1

    @staticmethod
    def _source_at_offset(boundaries, offset):
        """Find the source file at a given character offset."""
        for start, end, _, source in boundaries:
            if start <= offset < end:
                return source
        return boundaries[-1][3] if boundaries else ""
