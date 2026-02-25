"""EXE 실행 진입점.

Streamlit은 `streamlit run app.py` 명령어로 실행되므로,
exe에서는 이를 프로그래밍 방식으로 호출하는 래퍼가 필요.
"""

import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """PyInstaller 번들 환경과 일반 실행 환경 모두에서 올바른 기본 경로 반환."""
    if getattr(sys, "frozen", False):
        # PyInstaller exe로 실행 중
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def main() -> None:
    base_dir = get_base_dir()
    app_path = str(base_dir / "app.py")

    # Streamlit 설정: 브라우저 자동 열기, 포트 고정
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.headless=false",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--theme.base=light",
    ]

    # exe 실행 시 작업 디렉토리를 exe 위치로 설정
    # (products/, templates/ 등 데이터 파일 접근을 위해)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        os.chdir(exe_dir)

    from streamlit.web.cli import main as st_main
    st_main()


if __name__ == "__main__":
    main()
