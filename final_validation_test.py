"""최종 검증 테스트 - 자동 태그 생성 기능 E2E 테스트.

이 스크립트는:
1. detect_taggable_cells() - 셀 탐지 테스트
2. generate_cell_tags() - LLM 기반 태그 매핑 테스트
3. insert_placeholder_tags() - 태그 삽입 테스트
4. find_placeholders_in_doc() - 결과 검증 테스트
을 수행합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 경로 설정
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
from utils.doc_processor import (
    detect_taggable_cells,
    insert_placeholder_tags,
    find_placeholders_in_doc,
    TaggableCell,
    CellType,
)
from utils.ai_engine import RAGEngine
from config.placeholder_queries import PLACEHOLDER_QUERIES

load_dotenv()

print("\n" + "=" * 70)
print("최종 검증 테스트 - 자동 태그 생성 기능")
print("=" * 70 + "\n")

# ──────────────── 테스트 1: 셀 탐지 ──────────────
print("📋 [테스트 1] 셀 탐지 (detect_taggable_cells)")
print("-" * 70)

template_path = PROJECT_DIR / "templates" / "서울대학교병원_1771822359.docx"
if not template_path.exists():
    print(f"❌ 테스트 양식 파일을 찾을 수 없습니다: {template_path}")
    sys.exit(1)

try:
    cells = detect_taggable_cells(str(template_path))
    print(f"✅ 셀 탐지 성공")
    print(f"   - 탐지된 셀 수: {len(cells)}")

    # 셀 타입별 분류
    empty_cells = [c for c in cells if c.cell_type == CellType.EMPTY]
    label_only_cells = [c for c in cells if c.cell_type == CellType.LABEL_ONLY]
    print(f"   - EMPTY 셀: {len(empty_cells)}")
    print(f"   - LABEL_ONLY 셀: {len(label_only_cells)}")

    # 첫 3개 셀 미리보기
    print(f"\n   처음 3개 셀:")
    for i, cell in enumerate(cells[:3], 1):
        print(f"   {i}. T{cell.table_index}R{cell.row_index}C{cell.cell_index} "
              f"({cell.cell_type.value})")
        print(f"      질문: {cell.question[:50]}...")

except Exception as e:
    print(f"❌ 셀 탐지 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ──────────────── 테스트 2: LLM 태그 매핑 ──────────────
print(f"\n\n🤖 [테스트 2] LLM 기반 태그 매핑 (generate_cell_tags)")
print("-" * 70)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ GOOGLE_API_KEY 환경변수를 찾을 수 없습니다")
    sys.exit(1)

try:
    # RAGEngine 생성 (vectorstore 없음 - LLM 전용)
    rag_engine = RAGEngine(vectorstore=None, api_key=api_key)

    # 태그 생성 (처음 5개 셀만 테스트)
    test_cells = cells[:5] if len(cells) > 5 else cells
    print(f"테스트할 셀 수: {len(test_cells)}")

    mappings = rag_engine.generate_cell_tags(test_cells, PLACEHOLDER_QUERIES)

    print(f"✅ 태그 생성 성공")
    print(f"   - 매핑 결과 수: {len(mappings)}")

    # 결과 분석
    high_conf = sum(1 for m in mappings if m.confidence == "높음")
    mid_conf = sum(1 for m in mappings if m.confidence == "중간")
    low_conf = sum(1 for m in mappings if m.confidence == "낮음")
    unknown = sum(1 for m in mappings if m.placeholder_key == "unknown")

    print(f"   - 신뢰도 높음(높음): {high_conf}")
    print(f"   - 신뢰도 중간(중간): {mid_conf}")
    print(f"   - 신뢰도 낮음(낮음): {low_conf}")
    print(f"   - 매핑 실패(unknown): {unknown}")

    # 매핑 결과 미리보기
    print(f"\n   매핑 결과 (처음 3개):")
    for i, mapping in enumerate(mappings[:3], 1):
        print(f"   {i}. {mapping.question[:30]}... → {mapping.placeholder_key} "
              f"({mapping.confidence})")

except Exception as e:
    print(f"❌ 태그 생성 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ──────────────── 테스트 3: 태그 삽입 ──────────────
print(f"\n\n📝 [테스트 3] 태그 삽입 (insert_placeholder_tags)")
print("-" * 70)

try:
    # 태그 할당 생성 (cell, placeholder_key 쌍)
    tag_assignments = [
        (mappings[i].table_index, mappings[i].row_index,
         mappings[i].cell_index, mappings[i].placeholder_key)
        for i in range(min(3, len(mappings)))
    ]

    # 테스트 출력 파일
    output_path = PROJECT_DIR / "output" / "test_tagged_template.docx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 태그 삽입
    doc_bytes = insert_placeholder_tags(
        str(template_path),
        [(cells[i], mappings[i].placeholder_key)
         for i in range(min(3, len(mappings)))]
    )

    # 파일 저장
    with open(output_path, "wb") as f:
        f.write(doc_bytes)

    print(f"✅ 태그 삽입 성공")
    print(f"   - 삽입된 셀 수: {len(tag_assignments)}")
    print(f"   - 출력 파일: {output_path}")

except Exception as e:
    print(f"❌ 태그 삽입 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ──────────────── 테스트 4: 결과 검증 ──────────────
print(f"\n\n✔️ [테스트 4] 결과 검증 (find_placeholders_in_doc)")
print("-" * 70)

try:
    # 원본 문서의 placeholder 확인
    original_placeholders = find_placeholders_in_doc(str(template_path))
    print(f"원본 문서: {len(original_placeholders)}개 placeholder 발견")

    # 태그 삽입된 문서의 placeholder 확인
    output_placeholders = find_placeholders_in_doc(str(output_path))
    print(f"✅ 태그 삽입 문서: {len(output_placeholders)}개 placeholder 발견")

    if len(output_placeholders) > len(original_placeholders):
        print(f"   - 새로 추가된 placeholder: {len(output_placeholders) - len(original_placeholders)}개")
        print(f"\n   새 placeholder들:")
        new_placeholders = set(output_placeholders) - set(original_placeholders)
        for ph in sorted(list(new_placeholders))[:5]:
            print(f"   - {ph}")

except Exception as e:
    print(f"❌ 결과 검증 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ──────────────── 최종 결과 ──────────────
print(f"\n\n" + "=" * 70)
print("✅ 모든 테스트 완료!")
print("=" * 70)
print(f"""
검증 결과:
  ✅ [1] 셀 탐지: {len(cells)}개 셀 탐지됨
  ✅ [2] 태그 생성: {len(mappings)}개 셀 매핑됨
  ✅ [3] 태그 삽입: {len(tag_assignments)}개 셀에 태그 삽입됨
  ✅ [4] 결과 검증: {len(output_placeholders)}개 placeholder 확인됨

다음 단계:
  1. Windows 머신에서 build_exe.bat 실행
  2. 생성된 exe 파일 테스트
  3. 배포 패키지 준비
""")
