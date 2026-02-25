# DC Doc Generator - EXE 빌드 및 배포 가이드

## 📋 요구사항

### 개발자 (EXE 빌드하는 사람)
- **Windows 10 이상** (exe를 빌드하려면)
- **Python 3.9 이상** ⚠️ **개발자 머신에만 필요** (PyInstaller 사용하려면)
- **Google API Key** (Gemini AI 설정)

### 최종 사용자 (EXE를 받아서 실행하는 사람)
- **Windows 10 이상**
- **Python 설치 불필요** ✅ exe 안에 Python 런타임이 포함됨
- **Google API Key** (.env 파일에 입력)

## 🔧 빌드 절차

### Step 1: 소스 코드 준비

Windows 머신에서 프로젝트 폴더를 복사합니다:

```bash
# 프로젝트 폴더로 이동
cd "C:\Users\[YourName]\VibeCoding\Polivy\dc-doc-generator"
```

### Step 2: 자동 빌드 스크립트 실행

#### 옵션 A: 배치 파일 실행 (가장 간단함)

Windows 탐색기에서 프로젝트 폴더 내 `build_exe.bat` 파일을 **더블클릭**하면 자동으로:
1. 가상환경 생성
2. 의존성 설치
3. EXE 빌드
4. 필요한 폴더 복사

```
build_exe.bat 더블클릭 → 완료 메시지 표시 → Enter
```

#### 옵션 B: 수동 명령어 실행

```bash
# 1. 가상환경 생성 (처음 한 번만)
python -m venv venv

# 2. 가상환경 활성화
venv\Scripts\activate.bat

# 3. 의존성 설치
pip install -r requirements.txt
pip install pyinstaller

# 4. EXE 빌드 (5-10분 소요)
pyinstaller dc_doc_generator.spec --noconfirm

# 5. 데이터 폴더 복사
mkdir dist\DC_Doc_Generator\products
mkdir dist\DC_Doc_Generator\templates
xcopy /E /Y products dist\DC_Doc_Generator\products\
xcopy /E /Y templates dist\DC_Doc_Generator\templates\
xcopy /E /Y materials dist\DC_Doc_Generator\materials\

# 6. .env 파일 복사 (있으면)
copy .env dist\DC_Doc_Generator\.env
```

### Step 3: 빌드 결과 확인

빌드가 완료되면 다음 구조가 생성됩니다:

```
dist/
└── DC_Doc_Generator/
    ├── DC_Doc_Generator.exe          ← 메인 실행파일
    ├── products/                     ← 약품 Master Data
    ├── templates/                    ← 병원 양식
    ├── materials/                    ← 참고 자료
    ├── .env.example                  ← 설정 파일 템플릿
    └── [기타 파이썬 런타임 파일]
```

## 🚀 배포

### 배포 패키지 준비

1. **전체 `dist/DC_Doc_Generator/` 폴더를 압축**

```bash
# Windows PowerShell에서
Compress-Archive -Path "dist\DC_Doc_Generator" -DestinationPath "DC_Doc_Generator.zip"
```

또는 탐색기에서 우클릭 → 압축

2. **사용자에게 전달**

   - `DC_Doc_Generator.zip` 또는 전체 폴더 전달
   - Google API Key 설정 가이드 포함

### 사용자 설치 절차

사용자가 받은 후:

```
1. DC_Doc_Generator 폴더 압축 해제 (원하는 위치에)
   예: C:\Program Files\DC_Doc_Generator\

2. .env 파일 설정
   - 폴더 내 .env.example을 .env로 복사
   - .env 파일 열기
   - GOOGLE_API_KEY=YOUR_KEY_HERE 에 API 키 입력 후 저장

3. DC_Doc_Generator.exe 더블클릭으로 실행
   - 자동으로 브라우저에서 http://localhost:8501 로 열림
```

## 🔐 Google API Key 설정

### 1. API Key 발급받기

```
1. https://aistudio.google.com/app/apikey 방문
2. "Create API key" 버튼 클릭
3. "Create API key in new project" 선택
4. 생성된 키 복사
```

### 2. .env 파일에 입력

Windows PowerShell 또는 텍스트 에디터를 사용하여:

```bash
# .env 파일 내용 (텍스트 에디터로 열기)
GOOGLE_API_KEY=AIzaSyXXXXXXXXXX_복사한_키_XXXXXX
GEMINI_MODEL=gemini-2.0-flash
EMBEDDING_MODEL=models/gemini-embedding-001
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

**주의**: API 키는 절대 공개 저장소에 커밋하지 마세요. `.env` 파일은 배포 후 각 사용자가 자신의 키를 입력해야 합니다.

## 📦 배포 패키지 체크리스트

exe 배포 전 다음이 포함되어 있는지 확인하세요:

- [x] `DC_Doc_Generator.exe` (메인 실행파일)
- [x] `products/` 폴더 (약품 Master Data)
- [x] `templates/` 폴더 (등록된 병원 양식)
- [x] `materials/` 폴더 (참고 템플릿)
- [x] `.env.example` (API 키 설정 템플릿)
- [x] 모든 파이썬 런타임 파일들

## 🐛 트러블슈팅

### 문제 1: "DC_Doc_Generator.exe를 찾을 수 없습니다"

**원인**: 빌드 실패 또는 경로 오류

**해결책**:
```bash
# 빌드 폴더 정리 후 재시도
rmdir /s /q build dist
pyinstaller dc_doc_generator.spec --noconfirm
```

### 문제 2: "Google API Key 오류"

**원인**: .env 파일 설정 누락

**해결책**:
```bash
# exe와 같은 폴더에 .env 파일 있는지 확인
# .env 파일 내용:
GOOGLE_API_KEY=YOUR_API_KEY_HERE
```

### 문제 3: "포트 8501 이미 사용 중"

**원인**: Streamlit이 이미 실행 중

**해결책**:
```bash
# 기존 프로세스 종료
taskkill /IM DC_Doc_Generator.exe /F

# 또는 다른 포트에서 실행 (run_app.py 수정 필요)
```

### 문제 4: 빌드 중 "ModuleNotFoundError"

**원인**: 누락된 의존성

**해결책**:
```bash
# 의존성 재설치
pip install --upgrade -r requirements.txt
pip install --upgrade pyinstaller
```

## 📝 빌드 스크립트 커스터마이징

### 아이콘 추가

1. 256x256 PNG 아이콘을 ICO 형식으로 변환 (온라인 도구 또는 ImageMagick)
2. `icon.ico` 파일을 프로젝트 폴더에 복사
3. `dc_doc_generator.spec` 수정:

```python
icon="icon.ico",  # 라인 91
```

4. 재빌드

### 콘솔 창 숨기기

배포용으로 콘솔 창을 숨기려면 `dc_doc_generator.spec` 수정:

```python
console=False,  # 라인 90 (기본값: True)
```

## 🔄 버전 업데이트

새 버전 배포 시:

1. 소스 코드 업데이트
2. `build_exe.bat` 또는 빌드 명령어 재실행
3. `dist/DC_Doc_Generator/` 폴더 전체 교체

## 📞 지원

빌드 또는 배포 중 문제가 발생하면:

1. 콘솔 창에 표시되는 에러 메시지 복사
2. `.env` 파일 설정 확인
3. Windows Defender/백신 검사 (false positive 가능)

---

**마지막 빌드 날짜**: 2026-02-23
**Python 버전**: 3.9+
**Streamlit 버전**: 1.28+
