@echo off
chcp 65001 >nul
echo ============================================
echo   DC Doc Generator - EXE 빌드
echo ============================================
echo.

REM 가상환경 확인
if not exist "venv" (
    echo [1/4] 가상환경 생성 중...
    python -m venv venv
)

echo [1/4] 가상환경 활성화...
call venv\Scripts\activate.bat

echo [2/4] 의존성 설치 중...
pip install -r requirements.txt -q
pip install pyinstaller -q

echo [3/4] EXE 빌드 중 (몇 분 소요)...
pyinstaller dc_doc_generator.spec --noconfirm

echo [4/4] 데이터 폴더 복사 중...
REM products, templates 폴더는 exe와 같은 위치에 배치
if not exist "dist\DC_Doc_Generator\products" mkdir "dist\DC_Doc_Generator\products"
if not exist "dist\DC_Doc_Generator\templates" mkdir "dist\DC_Doc_Generator\templates"
xcopy /E /Y "products" "dist\DC_Doc_Generator\products\"
xcopy /E /Y "templates" "dist\DC_Doc_Generator\templates\"

REM .env 파일 복사 (있으면)
if exist ".env" copy ".env" "dist\DC_Doc_Generator\.env"
if exist ".env.example" copy ".env.example" "dist\DC_Doc_Generator\.env.example"

echo.
echo ============================================
echo   빌드 완료!
echo.
echo   결과물 위치:
echo     dist\DC_Doc_Generator\DC_Doc_Generator.exe
echo.
echo   배포 시 dist\DC_Doc_Generator 폴더 전체를 전달하세요.
echo   실행 전 .env 파일에 GOOGLE_API_KEY를 설정하세요.
echo ============================================
pause
