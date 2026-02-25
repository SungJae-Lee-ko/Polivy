# 🚀 빠른 시작 가이드 - DC Doc Generator 웹 배포

**5분 안에 웹 서버 실행하기**

---

## 1️⃣ 가장 간단한 방법: 로컬 웹 서버 (지금 바로 시작)

### 단계 1: 환경설정
```bash
# 1. 프로젝트 폴더로 이동
cd /Users/sungjaelee/VibeCoding/Polivy/dc-doc-generator

# 2. Google API Key 설정
export GOOGLE_API_KEY="your-api-key-here"

# 또는 .env 파일 생성
echo "GOOGLE_API_KEY=your-api-key-here" > .env
```

### 단계 2: 웹 서버 실행
```bash
streamlit run app.py
```

### 단계 3: 브라우저에서 접속
```
http://localhost:8501
```

**완료!** 🎉

---

## 2️⃣ Docker로 실행 (격리된 환경)

### 단계 1: Docker 이미지 빌드
```bash
docker build -t dc-doc-generator .
```

### 단계 2: 컨테이너 실행
```bash
docker run -p 8501:8501 \
  -e GOOGLE_API_KEY="your-api-key-here" \
  dc-doc-generator
```

### 단계 3: 브라우저에서 접속
```
http://localhost:8501
```

**또는 docker-compose 사용** (더 간단):
```bash
# .env 파일 생성
echo "GOOGLE_API_KEY=your-api-key-here" > .env

# 실행
docker-compose up
```

---

## 3️⃣ 클라우드에 배포 (Streamlit Cloud - 추천)

### 단계 1: GitHub에 업로드
```bash
git add .
git commit -m "Deploy to Streamlit Cloud"
git push origin main
```

### 단계 2: Streamlit Cloud 접속
- https://streamlit.io/cloud 방문
- GitHub 계정으로 로그인
- "New app" 클릭

### 단계 3: 앱 정보 입력
```
Repository: your-username/dc-doc-generator
Branch: main
Main file path: app.py
```

### 단계 4: API Key 설정
- App Settings → Secrets
- 다음 내용 추가:
```
GOOGLE_API_KEY = "your-api-key-here"
```

### 단계 5: 배포 완료!
```
앱 URL: https://your-app-name.streamlit.app
```

---

## 📊 배포 방식 비교

| 방식 | 설정 시간 | 비용 | 추천 상황 |
|------|---------|------|---------|
| **로컬 서버** | 1분 | 무료 | 개발/테스트 |
| **Docker** | 3분 | 무료 | 팀 개발 |
| **Streamlit Cloud** | 5분 | 무료 | 실제 배포 |
| **AWS/GCP** | 15분 | 유료 | 규모 배포 |

---

## 🔑 API Key 설정

### Google Gemini API Key 얻기

1. https://aistudio.google.com/app/apikey 방문
2. "Create API key" 클릭
3. "Create API key in new project" 선택
4. 생성된 키 복사

### 각 환경에서 설정

**로컬 (macOS/Linux)**:
```bash
export GOOGLE_API_KEY="AIzaSy..."
streamlit run app.py
```

**로컬 (Windows)**:
```bash
set GOOGLE_API_KEY=AIzaSy...
streamlit run app.py
```

**Docker**:
```bash
docker run -e GOOGLE_API_KEY="AIzaSy..." ...
```

**Streamlit Cloud**:
- App Settings → Secrets → `GOOGLE_API_KEY = "AIzaSy..."`

---

## ⚡ 팀 공유 (같은 네트워크)

### 로컬 IP 주소 확인
```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

### 팀원들이 접속
```
http://[your-ip-address]:8501
```

예: `http://192.168.1.100:8501`

---

## 🔧 포트 변경 (8501이 이미 사용 중일 때)

```bash
streamlit run app.py --server.port=8502
```

---

## 📁 프로젝트 구조

```
dc-doc-generator/
├── app.py                          ← 메인 Streamlit 앱
├── requirements.txt                ← Python 의존성
├── Dockerfile                      ← Docker 이미지
├── docker-compose.yml              ← Docker 구성
├── .dockerignore                   ← Docker 무시 파일
├── WEB_DEPLOYMENT_GUIDE.md         ← 상세 배포 가이드
├── QUICK_START.md                  ← 이 파일
├── config/
│   ├── settings.py                 ← 설정
│   ├── standard_fields.py          ← 표준 필드
│   └── placeholder_queries.py      ← 질의 템플릿
├── utils/
│   ├── doc_processor.py            ← 문서 처리
│   ├── ai_engine.py                ← AI 엔진
│   └── pdf_loader.py               ← PDF 로딩
├── products/                       ← 약품 데이터
├── templates/                      ← 병원 양식
└── materials/                      ← 참고 자료
```

---

## ❓ 자주 묻는 질문

### Q1: 여러 사람이 동시에 사용할 수 있나?
**A**:
- ✅ 로컬 서버: 같은 네트워크 가능
- ✅ Docker: 전용 서버 필요
- ✅ Streamlit Cloud: 무제한 동시 사용 가능

### Q2: 데이터는 저장되나?
**A**: 세션 기반으로 브라우저를 닫으면 삭제됨. 문서는 사용자가 다운로드해야 저장됨.

### Q3: API Key가 노출되나?
**A**: 아니요. 환경변수를 사용하므로 안전합니다.

### Q4: 오프라인에서도 사용 가능한가?
**A**: 아니요. Google Gemini API가 필요하므로 인터넷 연결 필수.

### Q5: 비용이 드나?
**A**:
- Streamlit Cloud: 무료
- Docker + AWS: 월 $5-10
- 자체 서버: 서버 비용만

---

## 🚀 다음 단계

### 개발자
1. `streamlit run app.py` 실행
2. 기능 테스트
3. Streamlit Cloud로 배포

### 운영 담당자
1. Streamlit Cloud 계정 생성
2. GitHub에 코드 연동
3. API Key 설정
4. 팀원들에게 URL 공유

### 최종 사용자
1. URL 접속
2. PDF 업로드
3. 병원 선택
4. 문서 생성 및 다운로드

---

## 📞 지원

**더 자세한 정보**: [WEB_DEPLOYMENT_GUIDE.md](WEB_DEPLOYMENT_GUIDE.md)

**문제 해결**: WEB_DEPLOYMENT_GUIDE.md의 "트러블슈팅" 섹션 참고

---

**준비 완료!** 이제 웹 배포를 시작하세요! 🎉
