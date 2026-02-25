"""PDF 텍스트 추출, 청킹, FAISS 벡터스토어 빌드."""

import logging
from pathlib import Path

import PyPDF2
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config.settings import CHUNK_OVERLAP, CHUNK_SIZE, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str | Path) -> list[Document]:
    """PDF 파일에서 페이지별 텍스트를 추출하여 LangChain Document 목록으로 반환.

    Args:
        file_path: PDF 파일 경로.

    Returns:
        페이지별 Document 목록. metadata에 source, page 포함.

    Raises:
        ValueError: 텍스트를 추출할 수 없는 경우 (빈 PDF 또는 스캔 이미지).
    """
    file_path = Path(file_path)
    documents: list[Document] = []

    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            text = text.strip()
            if not text:
                logger.warning(
                    "페이지 %d에서 텍스트를 추출하지 못했습니다: %s (스캔 이미지일 수 있음)",
                    page_num + 1,
                    file_path.name,
                )
                continue
            documents.append(
                Document(
                    page_content=text,
                    metadata={"source": file_path.name, "page": page_num + 1},
                )
            )

    if not documents:
        raise ValueError(
            f"'{file_path.name}'에서 텍스트를 추출할 수 없습니다. "
            "텍스트 기반 PDF인지 확인하세요."
        )

    return documents


def chunk_documents(
    documents: list[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """Document 목록을 일정 크기의 청크로 분할.

    Args:
        documents: LangChain Document 목록.
        chunk_size: 청크당 최대 문자 수.
        chunk_overlap: 인접 청크 간 겹치는 문자 수.

    Returns:
        청킹된 Document 목록. metadata에 chunk_id 추가.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    # chunk_id 추가
    for i, chunk in enumerate(chunks):
        source = chunk.metadata.get("source", "unknown")
        page = chunk.metadata.get("page", 0)
        chunk.metadata["chunk_id"] = f"{source}_p{page}_c{i}"

    return chunks


def build_vectorstore(
    file_paths: list[str | Path],
    api_key: str,
) -> FAISS:
    """PDF 파일들을 읽어 FAISS 인메모리 벡터스토어를 구축.

    Args:
        file_paths: PDF 파일 경로 목록.
        api_key: Google API 키.

    Returns:
        FAISS 벡터스토어 인스턴스 (인메모리, 세션 종료 시 휘발).

    Raises:
        ValueError: API 키가 없거나 모든 PDF에서 텍스트 추출에 실패한 경우.
    """
    if not api_key:
        raise ValueError("Google API 키가 필요합니다.")

    all_chunks: list[Document] = []
    failed_files: list[str] = []

    for path in file_paths:
        try:
            docs = extract_text_from_pdf(path)
            chunks = chunk_documents(docs)
            all_chunks.extend(chunks)
            logger.info("%s: %d개 청크 생성", Path(path).name, len(chunks))
        except ValueError as e:
            logger.warning("파일 처리 실패: %s", e)
            failed_files.append(str(path))

    if not all_chunks:
        raise ValueError(
            "처리 가능한 PDF가 없습니다. "
            f"실패한 파일: {', '.join(failed_files) if failed_files else '없음'}"
        )

    if failed_files:
        logger.warning("처리 실패한 파일: %s", ", ".join(failed_files))

    embedding = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=api_key,
    )
    vectorstore = FAISS.from_documents(all_chunks, embedding)
    logger.info("FAISS 벡터스토어 구축 완료: 총 %d개 청크", len(all_chunks))
    return vectorstore


def count_chunks_from_paths(file_paths: list[str | Path]) -> int:
    """PDF 파일들에서 예상 청크 수를 계산 (인덱싱 전 미리보기용).

    Args:
        file_paths: PDF 파일 경로 목록.

    Returns:
        예상 총 청크 수.
    """
    total = 0
    for path in file_paths:
        try:
            docs = extract_text_from_pdf(path)
            chunks = chunk_documents(docs)
            total += len(chunks)
        except ValueError:
            pass
    return total
