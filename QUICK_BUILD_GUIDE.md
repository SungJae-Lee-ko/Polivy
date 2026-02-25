# ⚡ Windows EXE 빌드 - 빠른 시작 가이드

## ⚠️ 중요: Python 설치 범위 명확히

| 누가 | Python 필요? | 이유 |
|-----|-----------|------|
| **개발자** (EXE 빌드) | ✅ 필요 | PyInstaller로 exe 생성하려면 필요 |
| **최종 사용자** (EXE 실행) | ❌ **불필요!** | exe 안에 Python 런타임 포함됨 |

→ **결론**: exe 파일 하나만 배포하면 사용자는 Python 설치 없이 바로 사용 가능합니다!

---

## 🎯 가장 간단한 방법 (5초)

1. **프로젝트 폴더 열기**
   ```
   C:\Users\[YourName]\VibeCoding\Polivy\dc-doc-generator\
   ```

2. **`build_exe.bat` 더블클릭**
   - 자동으로 모든 과정 진행 (5~10분 소요)
   - 완료 메시지가 나타나면 Enter 키 입력

3. **결과 확인**
   ```
   dist\DC_Doc_Generator\DC_Doc_Generator.exe
   ```

---

## 📦 빌드 후 배포

### 1. 압축
```powershell
# Windows PowerShell에서:
Compress-Archive -Path "dist\DC_Doc_Generator" -DestinationPath "DC_Doc_Generator.zip"
```

### 2. 사용자에게 전달
- `DC_Doc_Generator.zip` 전송
- 사용자가 받으면:
  1. 압축 해제
  2. `.env.example`을 `.env`로 복사
  3. `.env` 파일에 Google API Key 입력
  4. `DC_Doc_Generator.exe` 더블클릭

---

## 🔧 수동 빌드 (필요 시)

```bash
# 1. 프로젝트 폴더로 이동
cd C:\Users\[YourName]\VibeCoding\Polivy\dc-doc-generator

# 2. 가상환경 생성 (처음 한 번만)
python -m venv venv

# 3. 가상환경 활성화
venv\Scripts\activate.bat

# 4. 의존성 설치
pip install -r requirements.txt
pip install pyinstaller

# 5. EXE 빌드
pyinstaller dc_doc_generator.spec --noconfirm

# 6. 데이터 폴더 복사
mkdir dist\DC_Doc_Generator\products
mkdir dist\DC_Doc_Generator\templates
xcopy /E /Y products dist\DC_Doc_Generator\products\
xcopy /E /Y templates dist\DC_Doc_Generator\templates\
xcopy /E /Y materials dist\DC_Doc_Generator\materials\

# 7. 환경 파일 복사
copy .env.example dist\DC_Doc_Generator\.env.example
```

---

## ⚠️ 문제 해결

### Python을 찾을 수 없음
→ https://www.python.org에서 Python 3.9+ 설치 (PATH 추가 필수)

### build_exe.bat를 실행해도 아무것도 안 됨
→ 관리자 권한으로 CMD를 열고 `build_exe.bat` 실행

### 빌드 중 "ModuleNotFoundError"
→ 이전 빌드 정리 후 재시도:
```bash
rmdir /s /q build dist
build_exe.bat
```

### exe 실행 후 API Key 오류
→ `.env` 파일 생성 및 GOOGLE_API_KEY 값 확인

---

## 📋 체크리스트

### EXE 빌드 (개발자 - 1회만 필요)
- [ ] Windows 10 이상 (또는 Windows Server 2016+)
- [ ] **Python 3.9+ 설치됨** ⚠️ 개발자 머신에만 필요
- [ ] 프로젝트 폴더 복사됨
- [ ] `build_exe.bat` 실행 완료
- [ ] `dist\DC_Doc_Generator\DC_Doc_Generator.exe` 파일 생성됨
- [ ] `.env.example`을 `.env`로 복사하고 API Key 입력
- [ ] exe 파일 실행 후 브라우저 자동 열림 확인

### EXE 배포 (최종 사용자 - Python 불필요!)
- [ ] 배포 패키지 준비 완료
- [ ] `dist\DC_Doc_Generator\` 전체 또는 zip 파일 전송
- [ ] 사용자는 **Python 설치 없이** exe 바로 실행 가능

---

## 📚 자세한 정보

더 자세한 빌드 및 배포 가이드: [BUILD_AND_DEPLOY.md](BUILD_AND_DEPLOY.md)
빌드 검증 보고서: [BUILD_VERIFICATION.md](BUILD_VERIFICATION.md)

---

**Happy Building! 🚀**
