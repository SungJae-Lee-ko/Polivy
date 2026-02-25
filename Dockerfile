# Dockerfile - DC Doc Generator
# 사용법:
#   docker build -t dc-doc-generator .
#   docker run -p 8501:8501 -e GOOGLE_API_KEY="your-key" dc-doc-generator

FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 환경변수 (사용자가 docker run -e로 제공)
ENV GOOGLE_API_KEY=""
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Streamlit 설정 디렉토리 생성
RUN mkdir -p ~/.streamlit
RUN echo "[server]\nheadless = true\nport = 8501\naddress = 0.0.0.0" > ~/.streamlit/config.toml

# 포트 노출
EXPOSE 8501

# 헬스체크
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 앱 실행
CMD ["streamlit", "run", "app.py"]
