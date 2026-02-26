"""RAG 엔진: FAISS + Gemini 기반 의약품 DC 자료 질의응답."""

import json
import logging
import re
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_MODEL, RETRIEVER_K
from config.standard_fields import FIELD_QUERIES, STANDARD_FIELDS
from utils.doc_processor import TaggableCell

logger = logging.getLogger(__name__)

_RAG_PROMPT_TEMPLATE = """당신은 의약품 약제위원회(DC) 자료 작성을 돕는 전문가입니다.
제공된 의약품 Master Data에서 관련 정보를 찾아 한국어로 답변하세요.

규칙:
- 반드시 제공된 문서 내용에 근거하여 작성할 것
- 근거가 없으면 "해당 정보 없음"이라고만 답변
- 마크다운 형식(**, ##, *, - 등)을 사용하지 말 것. 순수 텍스트로만 작성
- 불필요한 서론, 머리말, "답변:" 같은 접두어 없이 바로 내용만 작성
- 병원 약제위원회 제출용으로 적합한 문어체 사용
- 숫자, 퍼센트, 통계값은 원문 그대로 정확히 인용

참고 문서:
{context}

질문: {question}

답변:"""


def _format_docs(docs: list[Document]) -> str:
    """검색된 Document 목록을 프롬프트용 텍스트로 변환."""
    return "\n\n".join(doc.page_content for doc in docs)

_FIELD_ANALYSIS_PROMPT = """아래는 병원 약제위원회(DC) 신청 양식의 내용입니다.
이 양식에서 작성해야 할 항목들을 파악하고, 아래 표준 필드 목록 중 가장 적합한 것에 매핑하세요.

표준 필드 목록:
{standard_fields}

병원 양식 내용:
{template_text}

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요:
{{
  "매핑 결과": [
    {{"양식_항목": "양식에서 발견된 질문 또는 항목명", "field_id": "표준 필드 ID", "확신도": "높음/중간/낮음"}},
    ...
  ]
}}

매핑할 수 없는 항목은 field_id를 "unknown"으로 설정하세요."""


@dataclass
class QueryResult:
    """RAG 질의 결과."""

    field_id: str
    answer: str
    sources: list[str] = field(default_factory=list)
    raw_chunks: list[Document] = field(default_factory=list)


@dataclass
class FieldMapping:
    """auto 모드 양식 분석 결과."""

    form_label: str
    field_id: str
    confidence: str


@dataclass
class CellTagMapping:
    """자동 태그 생성 결과 — 셀 좌표와 매핑된 placeholder 키."""

    table_index: int
    row_index: int
    cell_index: int
    question: str
    placeholder_key: str   # PLACEHOLDER_QUERIES 키 또는 "unknown"
    confidence: str        # "높음" / "중간" / "낮음"


_TAG_GENERATION_PROMPT = """병원 약제위원회(DC) 신청 양식의 각 셀을 분석하여, 가장 적합한 정보 필드를 매핑하세요.

## DC 신청 양식의 핵심 정보 6가지 (최우선 매핑 대상)
1. **indication_dosage** - 허가사항: 약물의 허가된 적응증, 용법용량, 투여방법, 투여기간
2. **application_reason** - 신청사유: 이 약을 병원에 도입해야 하는 이유, 필요성, 배경
3. **efficacy** - 효능/유효성: 임상시험 결과, 치료효과, 효과 데이터
4. **safety** - 안전성: 부작용, 이상반응, 주의사항, 금기, 안전성 프로파일
5. **cost_effectiveness** - 비용/경제성: 약가, 가격, 비용대비 효과, 경제성
6. **other_considerations** - 기타: 위 5가지에 해당하지 않는 추가 정보 (장점, 편리성, 모니터링 등)

## 분석할 양식 셀 목록
{cell_rows}

## 사용 가능한 모든 Placeholder 키
{placeholder_descriptions}

## 매핑 규칙
- 각 셀의 라벨/질문을 읽고, 위 6가지 DC 핵심 정보 카테고리 중 가장 가까운 것을 선택하세요
- 위 6가지 카테고리(indication_dosage, application_reason, efficacy, safety, cost_effectiveness, other_considerations)를 최우선으로 선택하세요
- 만약 세부 필드(예: "efficacy" 카테고리 내 "clinical_results")가 더 정확하면, 그 세부 필드를 선택해도 됩니다
- 매우 불명확한 경우에만 "unknown"을 사용하세요

## JSON 응답 형식
```json
{{
  "태그_매핑": [
    {{"cell_id": "T0R1C2", "placeholder_key": "efficacy", "확신도": "높음"}},
    {{"cell_id": "T0R1C3", "placeholder_key": "safety", "확신도": "중간"}},
    ...
  ]
}}
```

반드시 JSON만 출력하세요."""


class RAGEngine:
    """FAISS 벡터스토어와 Gemini LLM을 결합한 RAG 질의응답 엔진."""

    def __init__(self, vectorstore: FAISS | None, api_key: str) -> None:
        """RAGEngine 초기화.

        Args:
            vectorstore: 인덱싱된 FAISS 벡터스토어. None이면 LLM 전용 모드.
            api_key: Google API 키.
        """
        self._llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=api_key,
            temperature=0.1,
        )

        if vectorstore is not None:
            self._retriever = vectorstore.as_retriever(
                search_kwargs={"k": RETRIEVER_K}
            )
            self._vectorstore = vectorstore
            prompt = ChatPromptTemplate.from_template(_RAG_PROMPT_TEMPLATE)
            self._chain = (
                prompt
                | self._llm
                | StrOutputParser()
            )
        else:
            self._retriever = None
            self._vectorstore = None
            self._chain = None

    def query(
        self,
        field_id: str,
        custom_query: str | None = None,
    ) -> QueryResult:
        """표준 필드 ID 또는 커스텀 질의로 RAG 답변을 생성.

        Args:
            field_id: STANDARD_FIELDS의 필드 ID.
            custom_query: 커스텀 질의 텍스트. None이면 FIELD_QUERIES 기본값 사용.

        Returns:
            QueryResult (답변 텍스트, 출처 목록, 원본 청크 포함).
        """
        query_text = custom_query or FIELD_QUERIES.get(
            field_id,
            f"Please provide information about {field_id}.",
        )

        logger.info("RAG 질의 시작: field_id=%s", field_id)

        if self._chain is None or self._retriever is None:
            raise RuntimeError("vectorstore가 초기화되지 않았습니다. PDF 인덱싱을 먼저 수행하세요.")

        # 관련 청크 검색
        source_docs: list[Document] = self._retriever.invoke(query_text)
        context = _format_docs(source_docs)

        # 답변 생성
        answer: str = self._chain.invoke({
            "context": context,
            "question": query_text,
        })

        sources = list(
            {
                f"{doc.metadata.get('source', 'unknown')} p.{doc.metadata.get('page', '?')}"
                for doc in source_docs
            }
        )

        return QueryResult(
            field_id=field_id,
            answer=answer,
            sources=sorted(sources),
            raw_chunks=source_docs,
        )

    def query_batch(
        self,
        field_ids: list[str],
    ) -> list[QueryResult]:
        """여러 필드에 대해 순차적으로 RAG 질의를 수행.

        Args:
            field_ids: 질의할 필드 ID 목록.

        Returns:
            QueryResult 목록 (입력 순서 유지).
        """
        return [self.query(field_id) for field_id in field_ids]

    def analyze_template_fields(self, template_text: str) -> list[FieldMapping]:
        """auto 모드: 병원 양식 텍스트에서 작성 항목을 자동 인식하여 표준 필드에 매핑.

        Args:
            template_text: doc_processor.extract_doc_text()로 추출한 양식 전문.

        Returns:
            FieldMapping 목록. 매핑 실패 시 빈 리스트 반환.
        """
        fields_desc = "\n".join(
            f"- {fid}: {desc}" for fid, desc in STANDARD_FIELDS.items()
        )
        prompt = _FIELD_ANALYSIS_PROMPT.format(
            standard_fields=fields_desc,
            template_text=template_text[:8000],  # 토큰 제한 대비
        )

        try:
            response = self._llm.invoke(prompt)
            raw_text = response.content if hasattr(response, "content") else str(response)

            # JSON 파싱 시도
            parsed = self._parse_json_response(raw_text)
            mappings = parsed.get("매핑 결과", [])

            return [
                FieldMapping(
                    form_label=m.get("양식_항목", ""),
                    field_id=m.get("field_id", "unknown"),
                    confidence=m.get("확신도", "낮음"),
                )
                for m in mappings
                if isinstance(m, dict)
            ]
        except Exception as e:
            logger.error("양식 분석 실패: %s", e)
            return []

    def generate_cell_tags(
        self,
        cells: list[TaggableCell],
        placeholder_queries: dict[str, str],
    ) -> list[CellTagMapping]:
        """각 TaggableCell의 라벨을 PLACEHOLDER_QUERIES 키에 매핑.

        RAG 검색 없이 LLM만 직접 호출 (양식 구조 분석용).

        Args:
            cells: detect_taggable_cells()가 반환한 TaggableCell 목록.
            placeholder_queries: PLACEHOLDER_QUERIES 딕셔너리 (키 → 쿼리 문자열).

        Returns:
            CellTagMapping 목록. 파싱 실패 시 confidence="낮음", key="unknown".
        """
        if not cells:
            return []

        placeholder_descriptions = "\n".join(
            f'"{k}": "{v}"'
            for k, v in placeholder_queries.items()
        )

        cell_rows = "\n".join(
            f"T{c.table_index}R{c.row_index}C{c.cell_index} | {c.question}"
            for c in cells
        )

        prompt_text = _TAG_GENERATION_PROMPT.format(
            placeholder_descriptions=placeholder_descriptions,
            cell_rows=cell_rows,
        )

        # cell_id → TaggableCell 인덱스
        cell_index: dict[str, TaggableCell] = {
            f"T{c.table_index}R{c.row_index}C{c.cell_index}": c
            for c in cells
        }

        def _fallback_all() -> list[CellTagMapping]:
            """LLM 매핑 실패 시 모든 셀을 unknown으로 표시."""
            return [
                CellTagMapping(
                    table_index=c.table_index,
                    row_index=c.row_index,
                    cell_index=c.cell_index,
                    question=c.question,
                    placeholder_key="unknown",
                    confidence="낮음",
                )
                for c in cells
            ]

        try:
            response = self._llm.invoke(prompt_text)
            raw_text = response.content if hasattr(response, "content") else str(response)
            parsed = self._parse_json_response(raw_text)
            mappings_raw = parsed.get("태그_매핑", [])

            if not mappings_raw:
                logger.warning("LLM 태그 매핑 결과가 비어 있음")
                return _fallback_all()

            result: list[CellTagMapping] = []
            responded_ids: set[str] = set()

            for m in mappings_raw:
                if not isinstance(m, dict):
                    continue
                cid = m.get("cell_id", "")
                cell = cell_index.get(cid)
                if cell is None:
                    continue
                responded_ids.add(cid)
                result.append(CellTagMapping(
                    table_index=cell.table_index,
                    row_index=cell.row_index,
                    cell_index=cell.cell_index,
                    question=cell.question,
                    placeholder_key=m.get("placeholder_key", "unknown"),
                    confidence=m.get("확신도", "낮음"),
                ))

            # LLM이 응답하지 않은 셀은 unknown으로 추가
            for cid, cell in cell_index.items():
                if cid not in responded_ids:
                    result.append(CellTagMapping(
                        table_index=cell.table_index,
                        row_index=cell.row_index,
                        cell_index=cell.cell_index,
                        question=cell.question,
                        placeholder_key="unknown",
                        confidence="낮음",
                    ))

            return result

        except Exception as e:
            logger.error("태그 생성 실패: %s", e)
            return _fallback_all()

    def _parse_json_response(self, text: str) -> dict:
        """LLM 응답에서 JSON을 파싱. 실패 시 정규식으로 JSON 블록 추출 재시도."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 코드블록 제거 후 재시도
            cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`")
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        # JSON 객체 부분만 추출
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.warning("JSON 파싱 실패. 원본 응답: %s", text[:500])
        return {}
