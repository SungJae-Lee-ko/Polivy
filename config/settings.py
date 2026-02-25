"""앱 전역 설정 및 환경변수 관리."""

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_base_dir() -> Path:
    """PyInstaller exe 환경과 일반 실행 환경 모두에서 올바른 경로 반환.

    exe 실행 시: exe가 있는 폴더 (products/, templates/가 옆에 위치)
    일반 실행 시: 이 파일의 상위 폴더 (dc-doc-generator/)
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


BASE_DIR = _get_base_dir()

# LLM / Embedding
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

# RAG 청킹 설정
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", 200))
RETRIEVER_K: int = 5

# 파일 경로
PRODUCTS_JSON_PATH: Path = BASE_DIR / "products" / "products.json"
HOSPITAL_META_PATH: Path = BASE_DIR / "templates" / "hospital_meta.json"

# Placeholder 정규식 패턴
PLACEHOLDER_PATTERN: re.Pattern = re.compile(r"\{\{(\w+)\}\}")
