"""utils/ai_engine.py 단위 테스트."""

import json
from unittest.mock import MagicMock, patch

import pytest

from utils.ai_engine import FieldMapping, QueryResult, RAGEngine


# ───────── fixtures ─────────

def _make_mock_vectorstore():
    """FAISS 모의 객체."""
    vs = MagicMock()
    vs.as_retriever.return_value = MagicMock()
    return vs


def _make_engine_with_mocks(mock_llm_response: str = "테스트 답변") -> tuple[RAGEngine, MagicMock]:
    """RAGEngine을 Mock LLM과 함께 생성."""
    mock_vs = _make_mock_vectorstore()

    with patch("utils.ai_engine.ChatGoogleGenerativeAI") as mock_llm_cls, \
         patch("utils.ai_engine.RetrievalQA") as mock_qa_cls:

        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm

        mock_qa = MagicMock()
        mock_qa.invoke.return_value = {
            "result": mock_llm_response,
            "source_documents": [],
        }
        mock_qa_cls.from_chain_type.return_value = mock_qa

        engine = RAGEngine(mock_vs, api_key="fake-key")
        return engine, mock_qa


# ───────── RAGEngine 초기화 ─────────

class TestRAGEngineInit:
    def test_initializes_without_error(self):
        """RAGEngine이 오류 없이 초기화되는지 확인."""
        mock_vs = _make_mock_vectorstore()
        with patch("utils.ai_engine.ChatGoogleGenerativeAI"), \
             patch("utils.ai_engine.RetrievalQA"):
            engine = RAGEngine(mock_vs, api_key="fake-key")
            assert engine is not None


# ───────── query ─────────

class TestQuery:
    def test_returns_query_result(self):
        """query()가 QueryResult를 반환하는지 확인."""
        engine, _ = _make_engine_with_mocks("효능 데이터입니다.")
        result = engine.query("efficacy_summary")
        assert isinstance(result, QueryResult)

    def test_query_result_has_answer(self):
        """QueryResult에 answer 필드가 있는지 확인."""
        engine, _ = _make_engine_with_mocks("효능 데이터입니다.")
        result = engine.query("efficacy_summary")
        assert result.answer == "효능 데이터입니다."

    def test_query_result_field_id_matches(self):
        """QueryResult의 field_id가 입력값과 일치하는지 확인."""
        engine, _ = _make_engine_with_mocks()
        result = engine.query("safety_profile")
        assert result.field_id == "safety_profile"

    def test_custom_query_is_used(self):
        """custom_query가 있으면 해당 쿼리로 호출하는지 확인."""
        engine, mock_qa = _make_engine_with_mocks("커스텀 답변")
        result = engine.query("efficacy_summary", custom_query="커스텀 질의")
        assert result.answer == "커스텀 답변"
        mock_qa.invoke.assert_called_once_with({"query": "커스텀 질의"})

    def test_sources_are_extracted_from_docs(self):
        """source_documents에서 sources 목록이 추출되는지 확인."""
        mock_vs = _make_mock_vectorstore()

        with patch("utils.ai_engine.ChatGoogleGenerativeAI"), \
             patch("utils.ai_engine.RetrievalQA") as mock_qa_cls:
            mock_doc = MagicMock()
            mock_doc.metadata = {"source": "polivy_label.pdf", "page": 3}

            mock_qa = MagicMock()
            mock_qa.invoke.return_value = {
                "result": "답변",
                "source_documents": [mock_doc],
            }
            mock_qa_cls.from_chain_type.return_value = mock_qa

            engine = RAGEngine(mock_vs, api_key="fake-key")
            result = engine.query("efficacy_summary")

        assert "polivy_label.pdf p.3" in result.sources


# ───────── analyze_template_fields ─────────

class TestAnalyzeTemplateFields:
    def test_returns_field_mapping_list(self):
        """analyze_template_fields()가 FieldMapping 목록을 반환하는지 확인."""
        mock_vs = _make_mock_vectorstore()
        json_response = json.dumps({
            "매핑 결과": [
                {"양식_항목": "효능", "field_id": "efficacy_summary", "확신도": "높음"}
            ]
        })

        mock_llm_response = MagicMock()
        mock_llm_response.content = json_response

        with patch("utils.ai_engine.ChatGoogleGenerativeAI") as mock_llm_cls, \
             patch("utils.ai_engine.RetrievalQA"):
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_llm_response
            mock_llm_cls.return_value = mock_llm

            engine = RAGEngine(mock_vs, api_key="fake-key")
            mappings = engine.analyze_template_fields("양식 텍스트")

        assert len(mappings) == 1
        assert isinstance(mappings[0], FieldMapping)
        assert mappings[0].field_id == "efficacy_summary"

    def test_returns_empty_on_parse_failure(self):
        """JSON 파싱 실패 시 빈 리스트 반환."""
        mock_vs = _make_mock_vectorstore()
        mock_llm_response = MagicMock()
        mock_llm_response.content = "파싱 불가능한 텍스트"

        with patch("utils.ai_engine.ChatGoogleGenerativeAI") as mock_llm_cls, \
             patch("utils.ai_engine.RetrievalQA"):
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_llm_response
            mock_llm_cls.return_value = mock_llm

            engine = RAGEngine(mock_vs, api_key="fake-key")
            mappings = engine.analyze_template_fields("양식 텍스트")

        assert mappings == []


# ───────── _parse_json_response ─────────

class TestParseJsonResponse:
    def _get_engine(self):
        mock_vs = _make_mock_vectorstore()
        with patch("utils.ai_engine.ChatGoogleGenerativeAI"), \
             patch("utils.ai_engine.RetrievalQA"):
            return RAGEngine(mock_vs, api_key="fake-key")

    def test_valid_json(self):
        engine = self._get_engine()
        result = engine._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_code_block(self):
        engine = self._get_engine()
        result = engine._parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_invalid_json_returns_empty(self):
        engine = self._get_engine()
        result = engine._parse_json_response("완전히 파싱 불가능한 텍스트")
        assert result == {}
