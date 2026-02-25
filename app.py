"""DC 자료 자동화 앱 — Streamlit 메인 엔트리포인트."""

import json
import logging
import os
import sys
from pathlib import Path

import streamlit as st

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import HOSPITAL_META_PATH, PRODUCTS_JSON_PATH
from config.placeholder_queries import PLACEHOLDER_QUERIES
from utils.ai_engine import RAGEngine, CellTagMapping
from utils.doc_processor import (
    detect_taggable_cells,
    find_placeholders_in_doc,
    insert_placeholder_tags,
    replace_placeholders_to_bytes,
    TaggableCell,
    CellType,
)
from utils.pdf_loader import build_vectorstore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ───────────────────────────── 페이지 설정 ─────────────────────────────
st.set_page_config(
    page_title="DC 자료 자동화",
    page_icon="💊",
    layout="wide",
)

st.title("💊 DC 자료 자동화")
st.caption("병원 약제위원회(DC) 상정 자료를 AI로 자동 생성합니다.")


# ───────────────────────────── 유틸 함수 ─────────────────────────────
def _load_json(path: Path) -> dict:
    """JSON 파일 로드."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    """JSON 파일 저장."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _init_session_state() -> None:
    """Streamlit session state 초기화.

    RAG 엔진, 인덱싱 상태, 자동 태그 생성 상태 등을 초기화합니다.
    """
    defaults = {
        "google_api_key": os.getenv("GOOGLE_API_KEY", ""),
        "vectorstore": None,
        "rag_engine": None,
        "selected_product": None,
        "selected_hospital": None,
        "indexed_files": [],
        "indexed_chunks": 0,
        "generated_results": {},       # {질문 텍스트: 생성된 답변}
        "fillable_cells": [],          # FillableCell 목록
        "cell_fills": {},              # {(ti,ri,ci): 답변} — 최종 셀 채우기용
        # 자동 태그 생성 관련
        "tag_gen_cells": [],           # list[TaggableCell]
        "tag_gen_mappings": [],        # list[CellTagMapping]
        "tag_gen_template_path": None, # 분석 중인 템플릿 경로
        "tag_gen_hospital_id": None,   # 분석 중인 병원 ID
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_session_state()

TEMPLATES_DIR = Path("templates")
TEMPLATES_DIR.mkdir(exist_ok=True)


# ───────────────────────────── 사이드바 ─────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")

    # API Key
    api_key_input = st.text_input(
        "Google API Key",
        value=st.session_state.google_api_key,
        type="password",
        placeholder="AIza...",
        help="Google AI Studio에서 발급한 API 키",
    )
    if api_key_input != st.session_state.google_api_key:
        st.session_state.google_api_key = api_key_input
        st.session_state.rag_engine = None

    st.divider()

    # 제품 선택
    st.subheader("1️⃣ 제품 선택")
    try:
        products_data = _load_json(PRODUCTS_JSON_PATH)
        product_list = products_data.get("products", [])
    except FileNotFoundError:
        st.error(f"products.json을 찾을 수 없습니다: {PRODUCTS_JSON_PATH}")
        product_list = []

    if product_list:
        product_names = [p["name"] for p in product_list]
        selected_product_name = st.selectbox("제품", product_names, key="product_select")
        new_product = next(p for p in product_list if p["name"] == selected_product_name)

        if new_product != st.session_state.selected_product:
            st.session_state.selected_product = new_product
            st.session_state.vectorstore = None
            st.session_state.rag_engine = None
            st.session_state.indexed_files = []
            st.session_state.indexed_chunks = 0
            st.session_state.generated_results = {}
    else:
        st.warning("등록된 제품이 없습니다.")

    st.divider()

    # 병원 선택
    st.subheader("2️⃣ 병원 선택")
    try:
        hospital_data = _load_json(HOSPITAL_META_PATH)
        hospital_list = hospital_data.get("hospitals", [])
    except FileNotFoundError:
        hospital_list = []

    real_hospitals = [h for h in hospital_list if h.get("id") != "sample_hospital"]

    if real_hospitals:
        hospital_names = [h["name"] for h in real_hospitals]
        selected_hospital_name = st.selectbox("병원", hospital_names, key="hospital_select")
        new_hospital = next(h for h in real_hospitals if h["name"] == selected_hospital_name)

        if new_hospital != st.session_state.selected_hospital:
            st.session_state.selected_hospital = new_hospital
            st.session_state.generated_results = {}
            st.session_state.auto_mapping_done = False
            st.session_state.field_mapping = []

        mode_label = "수동 태그 ({{}})" if new_hospital.get("mode") == "manual" else "AI 자동 인식"
        st.caption(f"모드: **{mode_label}**")
    else:
        st.info("등록된 병원이 없습니다.\n\n**병원 양식 관리** 탭에서 추가하세요.")
        st.session_state.selected_hospital = None


# ───────────────────────────── 메인 탭 ─────────────────────────────
tab_generate, tab_hospitals = st.tabs(["📄 문서 생성", "🏥 병원 양식 관리"])


# ══════════════════════════════════════════════════════════════════
# 탭 1: 문서 생성
# ══════════════════════════════════════════════════════════════════
with tab_generate:
    product = st.session_state.selected_product
    hospital = st.session_state.selected_hospital
    api_key = st.session_state.google_api_key

    # ── Step 1: Master Data 관리 ──
    st.header("Step 1: Master Data (기준 문서) 업로드")

    if not product:
        st.info("사이드바에서 제품을 선택하세요.")
    else:
        master_data_dir = Path(product["master_data_dir"])
        master_data_dir.mkdir(parents=True, exist_ok=True)
        existing_pdfs = sorted(master_data_dir.glob("*.pdf"))

        col1, col2 = st.columns([3, 1])
        with col1:
            if existing_pdfs:
                st.success(f"저장된 PDF: **{len(existing_pdfs)}개** — {', '.join(f.name for f in existing_pdfs)}")
            else:
                st.warning("저장된 Master Data가 없습니다. PDF를 업로드하세요.")
        with col2:
            if existing_pdfs and st.button("🗑️ 초기화", help="저장된 PDF를 모두 삭제합니다"):
                for pdf in existing_pdfs:
                    pdf.unlink()
                st.session_state.vectorstore = None
                st.session_state.rag_engine = None
                st.session_state.indexed_files = []
                st.session_state.indexed_chunks = 0
                st.rerun()

        uploaded_files = st.file_uploader(
            "PDF 추가 업로드",
            type=["pdf"],
            accept_multiple_files=True,
            key="pdf_uploader",
        )
        if uploaded_files:
            for uf in uploaded_files:
                with open(master_data_dir / uf.name, "wb") as f:
                    f.write(uf.getbuffer())
            st.success(f"{len(uploaded_files)}개 파일 저장 완료")
            st.session_state.vectorstore = None
            st.session_state.rag_engine = None

        all_pdfs = sorted(master_data_dir.glob("*.pdf"))
        if all_pdfs:
            if st.session_state.vectorstore is None:
                if not api_key:
                    st.warning("Google API 키를 입력해야 인덱싱할 수 있습니다.")
                elif st.button("🔍 인덱싱 시작", type="primary"):
                    with st.spinner(f"{len(all_pdfs)}개 PDF 인덱싱 중..."):
                        try:
                            vectorstore = build_vectorstore(
                                file_paths=[str(p) for p in all_pdfs],
                                api_key=api_key,
                            )
                            st.session_state.vectorstore = vectorstore
                            st.session_state.rag_engine = RAGEngine(vectorstore, api_key)
                            st.session_state.indexed_files = [p.name for p in all_pdfs]
                            st.session_state.indexed_chunks = vectorstore.index.ntotal
                            st.rerun()
                        except Exception as e:
                            st.error(f"인덱싱 실패: {e}")
            else:
                st.success(
                    f"✅ 인덱싱 완료 — {len(st.session_state.indexed_files)}개 문서 / "
                    f"{st.session_state.indexed_chunks}개 청크"
                )

    st.divider()

    # ── Step 2: 문서 생성 ──
    st.header("Step 2: 문서 생성")

    rag_engine: RAGEngine | None = st.session_state.rag_engine

    if not rag_engine:
        st.info("Step 1에서 Master Data를 인덱싱하세요.")
    elif not hospital:
        st.info("사이드바에서 병원을 선택하세요. 병원이 없으면 **병원 양식 관리** 탭에서 먼저 등록하세요.")
    else:
        template_path = TEMPLATES_DIR / hospital["template_file"]

        if not template_path.exists():
            st.error(f"템플릿 파일을 찾을 수 없습니다: `{template_path}`")
            st.stop()

        # 양식 분석 — {{placeholder}} 태그 탐지
        placeholders = find_placeholders_in_doc(template_path)

        if not placeholders:
            st.warning(
                "양식에서 `{{태그}}` 항목을 찾지 못했습니다. "
                "템플릿에 `{{placeholder}}` 태그가 삽입되어 있는지 확인하세요."
            )
        else:
            st.info(f"양식에서 **{len(placeholders)}개 항목** 탐지 완료")

            with st.expander("탐지된 항목 목록", expanded=False):
                for i, key in enumerate(placeholders, 1):
                    query = PLACEHOLDER_QUERIES.get(key, key)
                    st.write(f"{i}. `{{{{{key}}}}}` — {query[:60]}")

            if st.button("🤖 문서 생성", type="primary", key="gen_auto"):
                progress = st.progress(0)
                status = st.empty()
                replacements: dict[str, str] = {}

                for i, key in enumerate(placeholders):
                    query_text = PLACEHOLDER_QUERIES.get(key, key)
                    status.write(f"처리 중: **{key}** ({i+1}/{len(placeholders)})")
                    try:
                        result = rag_engine.query(
                            field_id=key,
                            custom_query=query_text,
                        )
                        replacements[key] = result.answer
                    except Exception as e:
                        replacements[key] = f"[생성 실패: {e}]"
                        logger.error("질의 실패: %s — %s", key, e)
                    progress.progress((i + 1) / len(placeholders))

                st.session_state.generated_results = replacements

                status.empty()
                progress.empty()
                st.success(f"문서 생성 완료! ({len(replacements)}개 항목)")

    st.divider()

    # ── Step 3: 결과 확인 및 다운로드 ──
    st.header("Step 3: 결과 확인 및 다운로드")

    generated: dict[str, str] = st.session_state.generated_results

    if not generated:
        st.info("Step 2에서 문서를 생성하세요.")
    else:
        st.write(f"**{len(generated)}개 항목** 생성 완료. 내용을 확인하고 필요시 수정하세요.")

        edited_results: dict[str, str] = {}
        for i, (key, answer) in enumerate(generated.items()):
            query_desc = PLACEHOLDER_QUERIES.get(key, key)[:40]
            with st.expander(f"📄 {key} — {query_desc}", expanded=False):
                edited = st.text_area(
                    "내용",
                    value=answer,
                    height=200,
                    key=f"edit_{i}",
                    label_visibility="collapsed",
                )
                edited_results[key] = edited

        st.session_state.generated_results = edited_results

        st.divider()

        if hospital:
            template_path = TEMPLATES_DIR / hospital["template_file"]
            if template_path.exists() and edited_results:
                try:
                    doc_bytes = replace_placeholders_to_bytes(
                        doc_path=template_path,
                        replacements=edited_results,
                    )
                    product_name = product["id"] if product else "unknown"
                    hospital_name = hospital["id"] if hospital else "unknown"
                    download_name = f"DC_{product_name}_{hospital_name}.docx"

                    st.download_button(
                        label="⬇️ 완성된 .docx 다운로드",
                        data=doc_bytes,
                        file_name=download_name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="primary",
                    )
                except Exception as e:
                    st.error(f"파일 생성 실패: {e}")


# ══════════════════════════════════════════════════════════════════
# 탭 2: 병원 양식 관리
# ══════════════════════════════════════════════════════════════════
with tab_hospitals:
    st.header("🏥 병원 양식 관리")
    st.caption("병원별 DC 신청 양식(.docx)을 등록하고 관리합니다.")

    # ── 등록된 병원 목록 ──
    try:
        h_data = _load_json(HOSPITAL_META_PATH)
        h_list = h_data.get("hospitals", [])
    except FileNotFoundError:
        h_data = {"hospitals": []}
        h_list = []

    display_list = [h for h in h_list if h.get("id") != "sample_hospital"]

    st.subheader(f"등록된 병원 ({len(display_list)}개)")

    if display_list:
        for h in display_list:
            col_name, col_mode, col_file, col_del = st.columns([3, 1.5, 2, 1])
            col_name.write(f"**{h['name']}**")
            col_mode.write("수동" if h.get("mode") == "manual" else "AI 자동")
            col_file.write(f"`{h['template_file']}`")
            if col_del.button("삭제", key=f"del_{h['id']}"):
                # 병원 목록에서 제거
                h_data["hospitals"] = [x for x in h_data["hospitals"] if x["id"] != h["id"]]
                _save_json(HOSPITAL_META_PATH, h_data)
                # 템플릿 파일도 삭제
                tmpl = TEMPLATES_DIR / h["template_file"]
                if tmpl.exists():
                    tmpl.unlink()
                if st.session_state.selected_hospital and st.session_state.selected_hospital.get("id") == h["id"]:
                    st.session_state.selected_hospital = None
                st.rerun()
    else:
        st.info("등록된 병원이 없습니다. 아래에서 새 병원을 추가하세요.")

    st.divider()

    # ── 새 병원 추가 ──
    st.subheader("➕ 새 병원 추가")

    with st.form("add_hospital_form", clear_on_submit=True):
        hospital_name = st.text_input(
            "병원 이름 *",
            placeholder="예: 서울대학교병원",
        )

        template_file = st.file_uploader(
            "병원 양식 파일 업로드 * (.docx)",
            type=["docx"],
            help="병원에서 요구하는 DC 신청 양식 Word 파일을 업로드하세요.",
        )

        mode = st.radio(
            "양식 처리 방식",
            options=["auto", "manual"],
            format_func=lambda x: (
                "AI 자동 인식 — 원본 양식 그대로 업로드. AI가 항목을 자동으로 파악합니다. (권장)"
                if x == "auto"
                else "수동 태그 — 양식에 {{placeholder}} 태그를 직접 삽입한 경우 선택"
            ),
            help="AI 자동 인식 모드를 권장합니다.",
        )

        submitted = st.form_submit_button("병원 등록", type="primary")

    if submitted:
        if not hospital_name:
            st.error("병원 이름을 입력하세요.")
        elif not template_file:
            st.error("양식 파일을 업로드하세요.")
        else:
            # 병원 ID 생성 (이름 → 영문 소문자 + 타임스탬프)
            import re
            import time
            hospital_id = re.sub(r"[^a-zA-Z0-9가-힣]", "_", hospital_name).lower()
            hospital_id = f"{hospital_id}_{int(time.time())}"

            # 파일명: 병원ID.docx
            template_filename = f"{hospital_id}.docx"
            save_path = TEMPLATES_DIR / template_filename

            # 파일 저장
            with open(save_path, "wb") as f:
                f.write(template_file.getbuffer())

            # hospital_meta.json 업데이트
            new_entry = {
                "id": hospital_id,
                "name": hospital_name,
                "template_file": template_filename,
                "format": "docx",
                "mode": mode,
                "field_mapping": None,
            }
            h_data["hospitals"].append(new_entry)
            _save_json(HOSPITAL_META_PATH, h_data)

            st.success(f"✅ **{hospital_name}** 등록 완료! 사이드바에서 선택하여 사용하세요.")
            st.rerun()

    st.divider()

    # ── 자동 태그 생성 ──
    st.subheader("🏷️ 자동 태그 생성")
    st.caption(
        "원본 양식을 AI로 분석하여 각 항목에 {{placeholder}} 태그를 자동 삽입합니다. "
        "태그 삽입 후 '문서 생성' 탭에서 사용할 수 있습니다."
    )

    auto_hospitals = [h for h in display_list if h.get("mode") == "auto"]

    if not auto_hospitals:
        st.info("자동 태그 생성 대상 병원이 없습니다. 'AI 자동 인식' 모드로 등록된 병원만 대상입니다.")
    else:
        tag_target_names = [h["name"] + f" ({h['template_file']})" for h in auto_hospitals]
        tag_target_idx = st.selectbox(
            "태그 생성할 병원 선택",
            options=range(len(auto_hospitals)),
            format_func=lambda i: tag_target_names[i],
            key="tag_gen_hospital_select",
        )
        target_hospital = auto_hospitals[tag_target_idx]
        target_template_path = TEMPLATES_DIR / target_hospital["template_file"]

        col_analyze, col_reset = st.columns([1, 1])

        with col_analyze:
            if st.button("🔍 양식 분석", help="양식의 빈 셀과 라벨 셀을 탐지합니다"):
                with st.spinner("양식 구조 분석 중..."):
                    cells = detect_taggable_cells(target_template_path)
                    st.session_state.tag_gen_cells = cells
                    st.session_state.tag_gen_mappings = []
                    st.session_state.tag_gen_template_path = str(target_template_path)
                    st.session_state.tag_gen_hospital_id = target_hospital["id"]
                st.success(f"{len(cells)}개 후보 셀 탐지 완료")

        with col_reset:
            if st.button("초기화", help="분석 결과를 초기화합니다"):
                st.session_state.tag_gen_cells = []
                st.session_state.tag_gen_mappings = []
                st.session_state.tag_gen_template_path = None
                st.session_state.tag_gen_hospital_id = None
                st.rerun()

        # 탐지된 셀 표시 + AI 매핑 버튼
        tag_cells: list[TaggableCell] = st.session_state.tag_gen_cells
        if tag_cells:
            st.write(f"**{len(tag_cells)}개** 후보 셀이 탐지되었습니다.")

            with st.expander("탐지된 셀 목록", expanded=False):
                for c in tag_cells:
                    type_label = "빈 셀" if c.cell_type == CellType.EMPTY else "라벨 셀"
                    st.write(f"- T{c.table_index}R{c.row_index}C{c.cell_index} [{type_label}] — {c.question[:60]}")

            tag_api_key = st.session_state.google_api_key
            if not tag_api_key:
                st.warning("Google API 키를 입력해야 AI 태그 매핑을 실행할 수 있습니다.")
            elif st.button("🤖 자동 태그 생성", type="primary", key="gen_tags"):
                with st.spinner("AI가 각 셀에 적합한 태그를 분석 중..."):
                    # LLM 전용 RAGEngine 생성 (vectorstore 불필요)
                    tag_engine = RAGEngine(vectorstore=None, api_key=tag_api_key)
                    mappings = tag_engine.generate_cell_tags(
                        cells=tag_cells,
                        placeholder_queries=PLACEHOLDER_QUERIES,
                    )
                    st.session_state.tag_gen_mappings = mappings
                st.success(f"{len(mappings)}개 셀 태그 매핑 완료")

        # 매핑 결과 미리보기 + 편집
        tag_mappings: list[CellTagMapping] = st.session_state.tag_gen_mappings
        if tag_mappings and tag_cells:
            st.write("**태그 매핑 결과** — 아래에서 수정 후 '태그 삽입 확정'을 클릭하세요.")

            all_keys = ["(건너뜀)"] + sorted(PLACEHOLDER_QUERIES.keys())
            confidence_emoji = {"높음": "✅", "중간": "⚠️", "낮음": "❌"}

            cell_lookup: dict[tuple[int, int, int], TaggableCell] = {
                (c.table_index, c.row_index, c.cell_index): c for c in tag_cells
            }

            edited_assignments: list[tuple[TaggableCell, str]] = []

            for i, m in enumerate(tag_mappings):
                coord = (m.table_index, m.row_index, m.cell_index)
                cell = cell_lookup.get(coord)
                if cell is None:
                    continue

                emoji = confidence_emoji.get(m.confidence, "❓")
                label = f"{emoji} T{m.table_index}R{m.row_index}C{m.cell_index} | {m.question[:40]}"

                default_idx = (
                    all_keys.index(m.placeholder_key)
                    if m.placeholder_key in all_keys
                    else 0
                )

                selected_key = st.selectbox(
                    label,
                    options=all_keys,
                    index=default_idx,
                    key=f"tag_sel_{i}",
                )

                if selected_key != "(건너뜀)":
                    edited_assignments.append((cell, selected_key))
                    # 미리보기 텍스트
                    if cell.cell_type == CellType.LABEL_ONLY:
                        preview = f"{cell.current_text.rstrip()} {{{{{selected_key}}}}}"
                    else:
                        preview = f"{{{{{selected_key}}}}}"
                    st.caption(f"미리보기: `{preview}`")

            st.divider()

            if edited_assignments:
                # 미리보기 다운로드
                with st.expander("태그된 템플릿 미리보기 다운로드 (저장 전 확인)"):
                    preview_bytes = insert_placeholder_tags(
                        st.session_state.tag_gen_template_path,
                        edited_assignments,
                    )
                    st.download_button(
                        label="미리보기 다운로드",
                        data=preview_bytes,
                        file_name=f"tagged_preview_{target_hospital['template_file']}",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="tag_preview_dl",
                    )

                if st.button("✅ 태그 삽입 확정 및 저장", type="primary", key="confirm_tags"):
                    with st.spinner("태그 삽입 중..."):
                        tagged_bytes = insert_placeholder_tags(
                            st.session_state.tag_gen_template_path,
                            edited_assignments,
                        )

                    # 원본 위치에 저장
                    tag_save_path = Path(st.session_state.tag_gen_template_path)
                    with open(tag_save_path, "wb") as f:
                        f.write(tagged_bytes)

                    # hospital_meta.json 업데이트: mode → "manual"
                    target_id = st.session_state.tag_gen_hospital_id
                    for h in h_data["hospitals"]:
                        if h["id"] == target_id:
                            h["mode"] = "manual"
                            break
                    _save_json(HOSPITAL_META_PATH, h_data)

                    # session state 정리
                    st.session_state.tag_gen_cells = []
                    st.session_state.tag_gen_mappings = []
                    st.session_state.tag_gen_template_path = None
                    st.session_state.tag_gen_hospital_id = None

                    # 선택된 병원의 mode도 업데이트
                    if (st.session_state.selected_hospital
                            and st.session_state.selected_hospital.get("id") == target_id):
                        st.session_state.selected_hospital["mode"] = "manual"

                    st.success("태그 삽입 완료! 이제 '문서 생성' 탭에서 사용 가능합니다.")
                    st.rerun()
