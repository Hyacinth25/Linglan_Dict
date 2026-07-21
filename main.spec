# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 铃兰词典 — onedir portable build."""
import os

# ── Data files to bundle alongside the executable ──────────────────
added_datas = []

assets_dir = os.path.join(SPECPATH, "assets")
if os.path.isdir(assets_dir):
    added_datas.append((assets_dir, "assets"))

tips_file = os.path.join(SPECPATH, "tips.txt")
if os.path.isfile(tips_file):
    added_datas.append((tips_file, "."))

# ── Hidden imports ─────────────────────────────────────────────────
hiddenimports = [
    "openpyxl",
    "dotenv",
]

# ── Analysis ────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=added_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pip",
        "setuptools",
        "test",
        "tests",
        "unittest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# ── EXE (windowed, no console) ──────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="铃兰词典",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# ── Collect into onedir folder ──────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="铃兰词典",
)
