# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec 파일 — DC Doc Generator exe 빌드용.

빌드 명령:
    pyinstaller dc_doc_generator.spec

결과물:
    dist/DC_Doc_Generator/DC_Doc_Generator.exe
"""

import os
import importlib
from pathlib import Path

block_cipher = None

# Streamlit 패키지 위치 찾기
streamlit_dir = os.path.dirname(importlib.import_module("streamlit").__file__)

a = Analysis(
    ["run_app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # 앱 소스 코드
        ("app.py", "."),
        ("config", "config"),
        ("utils", "utils"),

        # Streamlit 런타임 파일 (정적 리소스, 설정 등)
        (streamlit_dir, "streamlit"),

        # 데이터 파일은 exe와 같은 폴더에 별도 배치 (아래 주석 참조)
    ],
    hiddenimports=[
        # Streamlit 내부 의존성
        "streamlit",
        "streamlit.web.cli",
        "streamlit.runtime.scriptrunner",

        # LangChain
        "langchain",
        "langchain.chains",
        "langchain.prompts",
        "langchain.schema",
        "langchain.text_splitter",
        "langchain_community",
        "langchain_community.vectorstores",
        "langchain_community.vectorstores.faiss",
        "langchain_google_genai",

        # Google AI
        "google.generativeai",
        "google.ai.generativelanguage",

        # 문서 처리
        "docx",
        "PyPDF2",
        "openpyxl",

        # 기타
        "faiss",
        "dotenv",
        "tiktoken",
        "tiktoken_ext",
        "tiktoken_ext.openai_public",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DC_Doc_Generator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 콘솔 창 표시 (로그 확인용, 배포 시 False로 변경 가능)
    icon=None,      # 아이콘 파일이 있으면 "icon.ico" 지정
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DC_Doc_Generator",
)
