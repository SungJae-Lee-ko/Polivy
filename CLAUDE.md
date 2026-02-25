# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DC Doc Generator** — 병원 약제위원회(DC) 상정 자료를 AI로 자동 생성하는 Streamlit 앱.
제품 Master Data(PDF)를 FAISS로 인덱싱하고, Gemini RAG로 병원별 Word 양식의 항목을 자동 채움.

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py

# 테스트 실행
pytest tests/

# 단일 테스트 파일 실행
pytest tests/test_doc_processor.py -v
```

## Architecture

- **`app.py`** — Streamlit 진입점. `st.session_state`로 vectorstore, rag_engine, 결과 관리.
- **`config/settings.py`** — 환경변수 로드 및 전역 상수 (PLACEHOLDER_PATTERN 포함).
- **`config/standard_fields.py`** — DC 자료 공통 필드 10종 정의. `FIELD_QUERIES`는 RAG에 전달할 영문 쿼리.
- **`utils/pdf_loader.py`** — PDF → LangChain Document → FAISS 인메모리 벡터스토어.
- **`utils/ai_engine.py`** — `RAGEngine` 클래스. `query(field_id)` → `QueryResult`. auto 모드 양식 분석은 `analyze_template_fields()`.
- **`utils/doc_processor.py`** — `.docx` placeholder 치환. run 분리 문제를 paragraph 전체 합산으로 해결.
- **`products/products.json`** — 제품 목록 및 master_data 경로. 코드 변경 없이 새 제품 추가 가능.
- **`templates/hospital_meta.json`** — 병원 목록. `mode: "manual"` ({{태그}}) 또는 `mode: "auto"` (AI 자동 인식).

## Key Patterns

**doc_processor의 run 분리 문제**: python-docx에서 `{{placeholder}}`가 여러 run으로 쪼개질 수 있음.
`_replace_in_paragraph()`에서 paragraph의 모든 run을 합산 후 치환하고 단일 run으로 재구성.

**새 제품 추가**: `products/products.json`에 항목 추가 + `products/{id}/master_data/` 폴더 생성.

**새 병원 추가**: `.docx` 템플릿을 `templates/`에 추가 + `hospital_meta.json`에 항목 추가.
