"""utils/pdf_loader.py 단위 테스트."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.pdf_loader import chunk_documents, extract_text_from_pdf


# ───────── fixtures ─────────

def _make_mock_reader(pages_text: list[str]):
    """PyPDF2.PdfReader 모의 객체 생성."""
    mock_reader = MagicMock()
    mock_pages = []
    for text in pages_text:
        page = MagicMock()
        page.extract_text.return_value = text
        mock_pages.append(page)
    mock_reader.pages = mock_pages
    return mock_reader


# ───────── extract_text_from_pdf ─────────

class TestExtractTextFromPdf:
    def test_normal_pdf_returns_documents(self, tmp_path):
        """정상 PDF에서 Document 목록 반환."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")

        mock_reader = _make_mock_reader(["Page 1 content", "Page 2 content"])
        with patch("utils.pdf_loader.PyPDF2.PdfReader", return_value=mock_reader):
            docs = extract_text_from_pdf(pdf_file)

        assert len(docs) == 2
        assert docs[0].page_content == "Page 1 content"
        assert docs[1].page_content == "Page 2 content"

    def test_metadata_contains_source_and_page(self, tmp_path):
        """metadata에 source와 page 필드 포함 확인."""
        pdf_file = tmp_path / "sample.pdf"
        pdf_file.write_bytes(b"dummy")

        mock_reader = _make_mock_reader(["Content"])
        with patch("utils.pdf_loader.PyPDF2.PdfReader", return_value=mock_reader):
            docs = extract_text_from_pdf(pdf_file)

        assert docs[0].metadata["source"] == "sample.pdf"
        assert docs[0].metadata["page"] == 1

    def test_empty_pages_are_skipped(self, tmp_path):
        """빈 페이지는 건너뜀."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")

        mock_reader = _make_mock_reader(["", "Valid content", ""])
        with patch("utils.pdf_loader.PyPDF2.PdfReader", return_value=mock_reader):
            docs = extract_text_from_pdf(pdf_file)

        assert len(docs) == 1
        assert docs[0].page_content == "Valid content"

    def test_all_empty_pages_raises_value_error(self, tmp_path):
        """모든 페이지가 비어있으면 ValueError 발생."""
        pdf_file = tmp_path / "empty.pdf"
        pdf_file.write_bytes(b"dummy")

        mock_reader = _make_mock_reader(["", "   ", None])
        with patch("utils.pdf_loader.PyPDF2.PdfReader", return_value=mock_reader):
            with pytest.raises(ValueError, match="텍스트를 추출할 수 없습니다"):
                extract_text_from_pdf(pdf_file)


# ───────── chunk_documents ─────────

class TestChunkDocuments:
    def test_chunks_are_created(self):
        """청크가 생성되는지 확인."""
        from langchain.schema import Document

        docs = [Document(page_content="A" * 3000, metadata={"source": "test.pdf", "page": 1})]
        chunks = chunk_documents(docs, chunk_size=500, chunk_overlap=50)

        assert len(chunks) > 1

    def test_chunk_has_chunk_id_metadata(self):
        """청크에 chunk_id metadata가 포함되는지 확인."""
        from langchain.schema import Document

        docs = [Document(page_content="Hello world " * 100, metadata={"source": "test.pdf", "page": 1})]
        chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)

        assert all("chunk_id" in c.metadata for c in chunks)

    def test_chunk_size_is_respected(self):
        """청크 크기가 chunk_size + overlap 이하인지 확인."""
        from langchain.schema import Document

        docs = [Document(page_content="X" * 5000, metadata={"source": "f.pdf", "page": 1})]
        chunk_size = 300
        chunk_overlap = 50
        chunks = chunk_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        for chunk in chunks:
            assert len(chunk.page_content) <= chunk_size + chunk_overlap

    def test_source_metadata_preserved(self):
        """원본 metadata(source, page)가 청크에 유지되는지 확인."""
        from langchain.schema import Document

        docs = [Document(
            page_content="Content " * 200,
            metadata={"source": "myfile.pdf", "page": 5},
        )]
        chunks = chunk_documents(docs)

        for chunk in chunks:
            assert chunk.metadata["source"] == "myfile.pdf"
            assert chunk.metadata["page"] == 5
