"""DC 자료 공통 질문 카테고리 (표준 필드 정의).

병원 양식들이 공통으로 요구하는 항목들을 표준화한 사전.
- STANDARD_FIELDS: 필드 ID → 한국어 설명 (UI 표시용)
- FIELD_QUERIES: 필드 ID → RAG에 전달할 영문 쿼리 (검색 정확도 최적화)
"""

STANDARD_FIELDS: dict[str, str] = {
    "efficacy_summary": "효능 및 유효성 데이터 요약",
    "safety_profile": "안전성 프로파일 및 이상반응",
    "dosage_administration": "용법·용량",
    "clinical_trials": "주요 임상시험 결과",
    "drug_interaction": "약물 상호작용",
    "contraindication": "금기사항",
    "pharmacokinetics": "약동학 정보",
    "storage_handling": "보관 및 취급",
    "cost_effectiveness": "비용 대비 효과",
    "comparison": "기존 치료제 대비 비교 우위",
}

FIELD_QUERIES: dict[str, str] = {
    "efficacy_summary": (
        "What are the efficacy and clinical outcomes data for this drug? "
        "Include response rates, survival data, and primary endpoint results."
    ),
    "safety_profile": (
        "What are the adverse events, safety profile, and toxicity data? "
        "Include incidence rates of serious adverse events and most common side effects."
    ),
    "dosage_administration": (
        "What is the recommended dosage and administration schedule for this drug? "
        "Include dose modifications and infusion guidelines."
    ),
    "clinical_trials": (
        "What are the key clinical trial results? "
        "Include trial names, patient populations, primary and secondary endpoints."
    ),
    "drug_interaction": (
        "What are the known drug interactions and contraindicated medications?"
    ),
    "contraindication": (
        "What are the contraindications and warnings for this drug? "
        "Include special populations such as pregnancy, hepatic/renal impairment."
    ),
    "pharmacokinetics": (
        "What are the pharmacokinetic properties? "
        "Include half-life, distribution, metabolism, and elimination data."
    ),
    "storage_handling": (
        "What are the storage conditions and handling instructions for this drug?"
    ),
    "cost_effectiveness": (
        "What is the cost-effectiveness or pharmacoeconomic data for this drug? "
        "Include comparison with standard of care."
    ),
    "comparison": (
        "How does this drug compare to existing treatments or standard of care? "
        "Include head-to-head data or indirect comparisons."
    ),
}
