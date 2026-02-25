# 웹 배포 가이드 - DC Doc Generator

**작성 일자**: 2026-02-23
**배포 방식**: Streamlit 웹 서버

---

## 🌐 배포 방식 비교

| 방식 | 설정 | 비용 | 속도 | 추천 |
|------|------|------|------|------|
| **1. 로컬 개발** | 극단순 | 무료 | 즉시 | ⭐⭐⭐ 개발용 |
| **2. Streamlit Cloud** | 간단 | 무료 | 5분 | ⭐⭐⭐⭐⭐ 추천 |
| **3. Docker + 클라우드** | 중간 | 유료 | 10분 | ⭐⭐⭐⭐ 규모 |
| **4. 개인 서버** | 복잡 | 유료 | 15분 | ⭐⭐⭐ 전용 |

---

## 1️⃣ 가장 간단한 방법: 로컬 웹 서버

### 한 명이 사용할 때 (개발/테스트)

```bash
# 1. 프로젝트 폴더로 이동
cd /Users/sungjaelee/VibeCoding/Polivy/dc-doc-generator

# 2. 환경변수 설정
export GOOGLE_API_KEY="your-api-key-here"

# 3. 웹 서버 실행
streamlit run app.py
```

**접속 주소**: `http://localhost:8501`

### 팀이 같은 네트워크에서 사용할 때

```bash
# 모두 같은 네트워크에 있으면:
streamlit run app.py

# 다른 팀원이 접속:
http://[your-ip-address]:8501
```

**IP 주소 확인**:
```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

---

## 2️⃣ 추천: Streamlit Cloud (무료, 가장 간단)

### 장점
- ✅ 무료
- ✅ 자동 배포 (GitHub 연동)
- ✅ SSL 자동 설정
- ✅ 실시간 업데이트

### 단계별 설치

#### 1단계: GitHub에 업로드
```bash
# 프로젝트를 GitHub에 푸시
git add .
git commit -m "Deploy to Streamlit Cloud"
git push origin main
```

#### 2단계: Streamlit Cloud 계정 생성
- https://streamlit.io/cloud 방문
- GitHub 계정으로 로그인
- "New app" 클릭

#### 3단계: 앱 배포
```
Repository: your-username/dc-doc-generator
Branch: main
Main file path: app.py
```

#### 4단계: 환경변수 설정
Settings → Secrets 클릭

```
# secrets.toml 형식
GOOGLE_API_KEY = "your-api-key-here"
```

### 결과
```
앱 URL: https://your-app-name.streamlit.app
```

---

## 3️⃣ 규모 있는 배포: Docker + AWS/GCP

### Docker 이미지 만들기

```dockerfile
# Dockerfile (프로젝트 루트에 생성)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV GOOGLE_API_KEY=""

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 로컬에서 Docker 테스트
```bash
# 이미지 빌드
docker build -t dc-doc-generator .

# 컨테이너 실행
docker run -p 8501:8501 \
  -e GOOGLE_API_KEY="your-api-key" \
  dc-doc-generator

# 접속: http://localhost:8501
```

### AWS EC2에 배포
```bash
# 1. EC2 인스턴스 생성 (Ubuntu 20.04)
# 2. SSH 연결
ssh -i your-key.pem ec2-user@your-instance-ip

# 3. Docker 설치
sudo apt-get update
sudo apt-get install docker.io -y

# 4. 프로젝트 클론
git clone https://github.com/your-repo/dc-doc-generator.git
cd dc-doc-generator

# 5. Docker 이미지 빌드 및 실행
sudo docker build -t dc-doc-generator .
sudo docker run -d -p 80:8501 \
  -e GOOGLE_API_KEY="your-api-key" \
  dc-doc-generator

# 6. 접속: http://your-instance-ip
```

---

## 4️⃣ 추가: 개인 Linux 서버

### Nginx + Streamlit 프록시 설정

```nginx
# /etc/nginx/sites-available/dc-doc-generator
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Systemd 서비스 설정
sudo nano /etc/systemd/system/dc-doc-generator.service

[Unit]
Description=DC Doc Generator
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/dc-doc-generator
Environment="GOOGLE_API_KEY=your-key"
ExecStart=/usr/bin/streamlit run app.py --server.port=8501

[Install]
WantedBy=multi-user.target

# 실행
sudo systemctl start dc-doc-generator
sudo systemctl enable dc-doc-generator
```

---

## 🔐 환경변수 설정

### 각 배포 방식별 설정

#### 로컬 (개발용)
```bash
# .env 파일 생성
echo "GOOGLE_API_KEY=your-key-here" > .env

# 또는 환경변수 설정
export GOOGLE_API_KEY="your-key-here"
streamlit run app.py
```

#### Streamlit Cloud
```
Settings → Secrets → secrets.toml
GOOGLE_API_KEY = "your-key-here"
```

#### Docker
```bash
docker run -e GOOGLE_API_KEY="your-key" ...
```

#### 서버 (Systemd)
```ini
Environment="GOOGLE_API_KEY=your-key"
```

---

## 📋 배포 전 체크리스트

### 코드 검증
- [ ] `requirements.txt` 최신화
- [ ] Python 버전 확인 (3.9+)
- [ ] API Key 하드코딩 제거
- [ ] `.env` 파일 `.gitignore`에 추가

### 보안 확인
- [ ] API Key 환경변수 사용
- [ ] 민감 정보 노출 확인
- [ ] 데이터 저장 위치 확인 (세션 메모리)

### 성능 확인
- [ ] 로컬에서 정상 실행 확인
- [ ] 대용량 PDF 테스트
- [ ] 동시 사용자 테스트

---

## 🚀 배포 후 모니터링

### 로그 확인

#### Streamlit Cloud
- Dashboard → App → Logs

#### 로컬/Docker
```bash
# 실시간 로그
streamlit run app.py --logger.level=info

# Docker 로그
docker logs container-name
```

### 성능 모니터링

#### 응답 시간
- PDF 인덱싱: 10-20초
- RAG 쿼리: 3-5초
- 문서 생성: <1초

#### 메모리 사용
- 기본: ~200MB
- PDF 인덱싱 시: ~500MB-1GB
- 동시 사용자 1명당: ~100MB 추가

---

## 🔧 트러블슈팅

### 문제 1: "API Key 오류"
```
❌ Google API Key 환경변수를 찾을 수 없습니다
```
**해결책**:
- Streamlit Cloud: Secrets에 GOOGLE_API_KEY 추가
- Docker: `-e GOOGLE_API_KEY="..."` 확인
- 로컬: `.env` 파일 확인

### 문제 2: "포트 8501 이미 사용 중"
```bash
# 다른 포트 사용
streamlit run app.py --server.port=8502
```

### 문제 3: "PDF 인덱싱 시간 초과"
```
⏱️ Streamlit Cloud 타임아웃 (300초)
```
**해결책**:
- 더 작은 PDF로 테스트
- Docker에서 타임아웃 증가:
```bash
docker run --timeout=600 ...
```

### 문제 4: "메모리 부족"
```
💾 메모리 초과 (Streamlit Cloud 1GB 제한)
```
**해결책**:
- FAISS 벡터스토어 최적화
- 임시 파일 정리
- Docker에서 메모리 증가

---

## 📊 선택 가이드

### 개발 단계
```
개발자 혼자 테스트
  ↓
로컬 웹 서버 (streamlit run app.py)
  ↓
누구든 접속 가능 (같은 네트워크)
```

### 소규모 팀 (병원 내)
```
몇 명만 사용
  ↓
Streamlit Cloud (추천!)
  ↓
자동 배포, 유지보수 최소
```

### 대규모 배포 (여러 병원)
```
많은 사용자
  ↓
Docker + AWS/GCP
  ↓
스케일링, 백업, 보안 완벽
```

---

## 📝 최종 정리

### 가장 빠른 배포 (5분)
1. GitHub에 코드 업로드
2. Streamlit Cloud 접속
3. 앱 생성 + API Key 설정
4. 완료!

### 비용
- **Streamlit Cloud**: 무료
- **Docker + AWS**: 월 5-10달러
- **개인 서버**: 월 10-50달러

### 권장 배포 방식
✅ **Streamlit Cloud** (가장 추천!)
- 설정 간단
- 자동 배포
- 무료
- 유지보수 없음

---

**배포 준비**: ✅ **준비 완료**

Streamlit Cloud 배포로 전환하시겠어요? 또는 다른 방식을 원하시나요?
