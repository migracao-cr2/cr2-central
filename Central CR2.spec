# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["src/app_qt.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("catalogo.json", "."),
        ("logo.ico", "."),
        ("src/logo.png", "src"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "tkinter",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Central CR2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="logo.ico",
)
