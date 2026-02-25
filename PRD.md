# PRD: 병원 DC 자료 자동화 (DC Doc Generator)

## 1. 문제 정의 (Problem Statement)

제약회사에서 의약품의 병원별 약제위원회(DC) 상정 자료를 작성하는 과정이 완전 수작업으로 진행되고 있다. 이 문제는 Polivy뿐 아니라 **모든 제품**에 동일하게 발생한다.

| 항목 | 현황 |
|------|------|
| 대상 병원 수 | 42개 |
| 병원별 양식 | 모두 상이 (Word/Excel) |
| 데이터 소스 | Global 본사 Master Data (임상 논문, 제품 설명서 PDF) — **제품별로 다름** |
| 작업 방식 | 담당자가 PDF를 읽고 → 병원 양식에 맞게 수동 작성 |
| 핵심 고통점 | 동일한 데이터를 42가지 다른 포맷으로 반복 작성, **제품이 바뀔 때마다 처음부터 반복** |

## 2. 솔루션 개요 (Solution)

**제품을 선택하고 Master Data(PDF)를 업로드하면, 선택한 병원 양식의 항목을 AI가 자동으로 채워주는 웹 애플리케이션**

- 첫 번째 타겟 제품: Polivy (항암제)
- 동일한 도구로 다른 제품(예: Tecentriq, Avastin 등)에도 바로 적용 가능

### 핵심 플로우
```
[제품 선택] → [PDF 업로드] → [Vector DB 인덱싱] → [병원 선택] → [양식 항목별 RAG 질의] → [.docx 자동 생성] → [다운로드]
```

## 3. 기술 아키텍처 (Technical Architecture)

### 3.1 기술 스택

| 레이어 | 기술 | 선정 이유 |
|--------|------|-----------|
| Language | Python 3.9+ | 데이터/AI 생태계 최적 |
| UI | Streamlit | 빠른 프로토타이핑, Local/Cloud 배포 용이 |
| LLM Orchestration | LangChain | RAG 체인 구성, 프롬프트 관리 |
| LLM | Google Gemini (gemini-2.0-flash 또는 gemini-2.5-pro) | 한국어 우수, 비용 효율적, 긴 컨텍스트 |
| Embedding | Google Generative AI Embeddings (models/embedding-001) | Gemini 생태계 통합 |
| Vector DB | FAISS | 인메모리, 설치 간편, 세션 종료 시 자동 휘발 |
| Word 처리 | python-docx | .docx 읽기/쓰기 |
| PDF 처리 | PyPDF2 + LangChain Document Loaders | PDF 텍스트 추출 |
| Excel 처리 | openpyxl | .xlsx 읽기/쓰기 |
| 배포 | 개별 PC 로컬 실행 | Streamlit 로컬 서버로 브라우저 접속 |

### 3.2 프로젝트 구조

```
dc-doc-generator/
├── app.py                        # Streamlit 메인 앱
├── requirements.txt
├── .env.example                  # 환경변수 템플릿
├── config/
│   ├── settings.py               # 앱 설정 (모델명, chunk size 등)
│   └── standard_fields.py        # 공통 질문 카테고리 (표준 필드 정의)
├── utils/
│   ├── __init__.py
│   ├── ai_engine.py              # RAG 체인 (PDF 인덱싱 + 질의응답)
│   ├── doc_processor.py          # .docx 플레이스홀더 치환 엔진
│   └── pdf_loader.py             # PDF 텍스트 추출 및 청킹
├── products/                     # 제품별 데이터 관리
│   ├── products.json             # 등록된 제품 목록
│   ├── polivy/
│   │   └── master_data/          # Polivy Master Data PDF 저장소
│   └── tecentriq/
│       └── master_data/          # 다른 제품 예시
├── templates/                    # 병원별 .docx 템플릿 (제품 공통)
│   ├── hospital_meta.json        # 병원 목록 및 메타데이터
│   └── {hospital_name}.docx      # 각 병원 양식
└── tests/
    ├── test_ai_engine.py
    ├── test_doc_processor.py
    └── test_pdf_loader.py
```

### 3.3 모듈별 책임

#### `products/` — 제품 및 Master Data 관리

**핵심 개념**: 병원 양식(templates/)은 제품과 무관하게 공통이고, Master Data만 제품별로 다름.

```json
// products/products.json
{
  "products": [
    {
      "id": "polivy",
      "name": "Polivy (polatuzumab vedotin)",
      "category": "항암제",
      "master_data_dir": "products/polivy/master_data/"
    },
    {
      "id": "tecentriq",
      "name": "Tecentriq (atezolizumab)",
      "category": "항암제",
      "master_data_dir": "products/tecentriq/master_data/"
    }
  ]
}
```

**Master Data 관리 방식**:

| 시나리오 | 동작 |
|----------|------|
| **최초 등록** | 제품 폴더 생성 → `master_data/`에 PDF 저장 |
| **데이터 업데이트** | 새 PDF 업로드 시 기존 인덱스 폐기 → 재인덱싱 |
| **매번 업로드 vs 저장** | 기본은 `master_data/`에 로컬 저장하여 재사용. 매번 업로드도 가능 |
| **새 제품 추가** | products.json에 항목 추가 + 폴더 생성 (코드 변경 불필요) |

> 인메모리 원칙은 "세션 중 처리되는 중간 데이터"에 적용. Master Data PDF 원본은 로컬 PC에 저장하여 매번 업로드하지 않아도 되도록 함.

#### `utils/pdf_loader.py` — PDF 처리
- PDF 파일을 텍스트로 추출
- LangChain `RecursiveCharacterTextSplitter`로 청킹 (chunk_size=1000, overlap=200)
- 청크를 FAISS 벡터 스토어에 인덱싱
- 복수 PDF 동시 업로드 지원

#### `utils/ai_engine.py` — RAG 엔진
- FAISS 벡터 스토어 기반 retriever 구성
- 병원 양식 항목(질문)을 받아 관련 청크를 검색하고 Gemini로 답변 생성
- 프롬프트 템플릿: 의약품 DC 자료 맥락에 특화된 시스템 프롬프트
- 답변 언어: 한국어 (병원 양식이 한국어)
- 답변에 출처(source) 표기 포함

#### `utils/doc_processor.py` — 문서 생성
- .docx 파일에서 `{{placeholder}}` 패턴 탐색
- placeholder → AI 생성 텍스트로 치환
- 테이블 셀 내부의 placeholder도 처리
- 원본 서식(폰트, 크기, 볼드 등) 유지

#### 템플릿 관리 전략

**현황**: 42개 병원 양식을 이미 Word/Excel 파일로 보유. 질문 항목은 병원 간 대부분 유사(효능, 안전성, 용법 등)하나 포맷/레이아웃이 다름.

**공통 질문 카테고리 (Standard Fields)**

병원 양식들이 공통으로 묻는 항목을 표준화하여 관리:

```python
# config/standard_fields.py
STANDARD_FIELDS = {
    "efficacy_summary": "약물의 효능 및 유효성 데이터 요약",
    "safety_profile": "안전성 프로파일 및 이상반응 정보",
    "dosage_administration": "용법·용량 정보",
    "clinical_trials": "주요 임상시험 결과",
    "drug_interaction": "약물 상호작용",
    "contraindication": "금기사항",
    "pharmacokinetics": "약동학 정보",
    "storage_handling": "보관 및 취급 방법",
    "cost_effectiveness": "비용 대비 효과",
    "comparison": "기존 치료제 대비 비교 우위",
}
```

**Placeholder 인식 — 2가지 모드 지원**

| 모드 | 설명 | 사용 시점 |
|------|------|-----------|
| **수동 태그** | 담당자가 .docx에 `{{efficacy_summary}}` 형태로 미리 삽입 | 양식 정리가 완료된 병원 |
| **AI 자동 인식** | 원본 양식을 그대로 업로드 → AI가 빈칸/질문 항목을 자동 파악 후 standard field에 매핑 | 태그 작업 전 또는 빠른 처리 시 |

**AI 자동 인식 플로우**:
```
[원본 .docx 업로드] → [문서 텍스트 추출] → [Gemini가 질문 항목 파악]
→ [standard field에 매핑] → [사용자 확인/수정] → [답변 생성 및 삽입]
```

**`templates/hospital_meta.json` — 병원 메타데이터**
```json
{
  "hospitals": [
    {
      "id": "seoul_national",
      "name": "서울대학교병원",
      "template_file": "seoul_national.docx",
      "format": "docx",
      "mode": "manual",
      "field_mapping": {
        "efficacy_summary": "{{efficacy_summary}}",
        "safety_profile": "{{safety_profile}}"
      }
    },
    {
      "id": "asan_medical",
      "name": "서울아산병원",
      "template_file": "asan_medical.docx",
      "format": "docx",
      "mode": "auto",
      "field_mapping": null
    }
  ]
}
```

- `mode: "manual"` → 이미 `{{태그}}`가 삽입된 템플릿, field_mapping으로 직접 매핑
- `mode: "auto"` → 원본 양식 그대로, AI가 질문 항목을 자동 인식하여 매핑
- 새 병원 추가 시: .docx 파일 추가 + JSON에 항목 추가 (코드 변경 불필요)

## 4. 기능 상세 (Feature Specification)

### 4.1 F1: 제품 선택 및 Master Data 관리

| 항목 | 내용 |
|------|------|
| 제품 선택 | 사이드바 드롭다운 (products.json 기반) |
| 기존 데이터 | 선택한 제품의 `master_data/`에 PDF가 있으면 자동 로드 |
| 신규 업로드 | 추가 PDF 업로드 가능 → `master_data/`에 저장 + 인덱싱 |
| 데이터 갱신 | "Master Data 초기화" 버튼 → 기존 PDF 삭제 후 새로 업로드 |
| 처리 | 텍스트 추출 → 청킹 → FAISS 인메모리 인덱싱 |
| 출력 | "N개 문서, M개 청크 인덱싱 완료" 상태 메시지 |
| 에러 처리 | 빈 PDF, 스캔 이미지 PDF(텍스트 없음) 시 경고 |

### 4.2 F2: 병원 템플릿 선택

| 항목 | 내용 |
|------|------|
| UI | 사이드바 드롭다운 (hospital_meta.json 기반) |
| 동작 (manual 모드) | 선택 시 해당 병원의 placeholder 목록 표시 |
| 동작 (auto 모드) | 선택 시 AI가 양식을 분석하여 질문 항목을 자동 추출 → standard field에 매핑 → 사용자 확인/수정 |

### 4.3 F3: AI 자동 채우기

| 항목 | 내용 |
|------|------|
| 트리거 | "문서 생성" 버튼 클릭 |
| 처리 (manual) | {{placeholder}}별로 RAG 질의 → 답변 생성 → .docx에 삽입 |
| 처리 (auto) | AI가 인식한 질문 위치에 직접 답변 삽입 |
| 진행률 | 처리 중 항목별 상태 실시간 표시 (Streamlit progress bar + 로그) |
| 소요시간 | 항목 1개당 약 3-5초 예상 |

### 4.4 F4: 미리보기 및 다운로드

| 항목 | 내용 |
|------|------|
| 미리보기 | 생성된 내용을 항목별로 화면에 텍스트 표시 |
| 수정 | 사용자가 생성된 텍스트를 수정 가능 (text_area) |
| 다운로드 | 최종 .docx 파일 다운로드 버튼 |

## 5. UI 레이아웃

```
┌──────────────────────────────────────────────────────┐
│  DC 자료 자동화 (DC Doc Generator)                    │
├───────────┬──────────────────────────────────────────┤
│ SIDEBAR   │  MAIN AREA                               │
│           │                                          │
│ [API Key] │  ┌─ Step 1: Master Data ───────────────┐ │
│           │  │  저장된 PDF: 3개 (245페이지)         │ │
│ [제품 ▼]  │  │  [추가 업로드]  [초기화]            │ │
│  Polivy   │  │  "3개 문서 / 127개 청크 인덱싱 완료"│ │
│           │  └────────────────────────────────────┘ │
│ [병원 ▼]  │                                          │
│  서울대   │  ┌─ Step 2: 문서 생성 ─────────────────┐ │
│           │  │  [문서 생성 버튼]                    │ │
│           │  │  ■■■■■□□□□□ 5/10 항목 처리중...     │ │
│           │  └────────────────────────────────────┘ │
│           │                                          │
│           │  ┌─ Step 3: 결과 확인 ─────────────────┐ │
│           │  │  항목1: efficacy_summary             │ │
│           │  │  [생성된 텍스트 미리보기/수정]       │ │
│           │  │  항목2: safety_profile               │ │
│           │  │  [생성된 텍스트 미리보기/수정]       │ │
│           │  │  ...                                 │ │
│           │  │  [.docx 다운로드 버튼]               │ │
│           │  └────────────────────────────────────┘ │
└───────────┴──────────────────────────────────────────┘
```

## 6. 개발 계획 (3주 스프린트)

### Week 1: 기반 구축
| 일차 | 작업 | 산출물 |
|------|------|--------|
| Day 1-2 | 프로젝트 스캐폴딩 + 환경설정 | 폴더구조, requirements.txt, settings.py |
| Day 3-4 | pdf_loader.py + ai_engine.py 구현 | PDF→FAISS 인덱싱, RAG 질의응답 동작 |
| Day 5 | 단위 테스트 작성 + 검증 | tests/ 통과 |

### Week 2: 문서 처리 + UI
| 일차 | 작업 | 산출물 |
|------|------|--------|
| Day 6-7 | doc_processor.py 구현 | placeholder 치환 엔진 (서식 유지) |
| Day 8-9 | Streamlit app.py 구현 | 전체 UI 플로우 동작 |
| Day 10 | 통합 테스트 (PDF 업로드 → docx 생성 E2E) | 샘플 병원 1개로 E2E 성공 |

### Week 3: 확장 + 품질
| 일차 | 작업 | 산출물 |
|------|------|--------|
| Day 11-12 | 병원 템플릿 등록 (5-10개 병원) | templates/ 에 실제 양식 반영 |
| Day 13 | 프롬프트 튜닝 + 답변 품질 개선 | 의약품 도메인 최적화 프롬프트 |
| Day 14 | 에러 핸들링, 엣지케이스 처리 | 안정성 확보 |
| Day 15 | 사용자 테스트 + 버그 수정 | MVP 릴리즈 |

## 7. 설정 및 환경 변수

```env
# .env.example
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EMBEDDING_MODEL=models/embedding-001
```

## 8. 제약 사항 및 고려 사항

### 보안
- 모든 문서 처리는 인메모리(세션 종료 시 휘발)
- Google API Key는 환경변수 또는 Streamlit 사이드바 입력 (코드에 하드코딩 금지)
- 업로드 파일은 디스크에 저장하지 않음 (로컬 실행이지만 인메모리 원칙 유지)

### 확장성
- 새 제품 추가: products.json에 항목 추가 + `products/{id}/master_data/`에 PDF 저장 (코드 변경 불필요)
- 새 병원 추가: .docx 템플릿 + hospital_meta.json 항목 추가만으로 가능
- Master Data 갱신: 해당 제품 폴더의 PDF 교체 후 재인덱싱
- LLM 교체: ai_engine.py의 모델 설정만 변경 (LangChain 추상화로 용이)

### 한계 및 향후 개선
- **스캔 PDF**: 현재 텍스트 기반 PDF만 지원 → 향후 OCR(Tesseract) 연동 가능
- **테이블/이미지**: PDF 내 테이블 구조 추출은 제한적 → 향후 테이블 파서 추가
- **동시 병원 생성**: 현재 1개 병원씩 → 향후 배치 생성 기능
- **답변 품질 검증**: 사용자 리뷰 단계에서 수동 확인 필요

## 9. 성공 기준 (Definition of Done)

- [ ] PDF 업로드 후 FAISS 인덱싱 정상 동작
- [ ] 샘플 병원 템플릿으로 전체 E2E 플로우 성공
- [ ] 생성된 .docx 파일의 서식이 원본 템플릿과 동일
- [ ] placeholder별 AI 답변이 Master Data 기반으로 정확
- [ ] 세션 종료 시 모든 데이터 휘발 확인
- [ ] 5개 이상 병원 템플릿으로 테스트 완료
