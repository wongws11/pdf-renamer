# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/pdf_renamer/__main__.py'],
    pathex=['src', '.'],
    binaries=[],
    datas=[],
    hiddenimports=['pdf2image', 'requests', 'PIL', 'sqlite3', 'pdf_renamer.cli', 'pdf_renamer.pdf_utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='pdf-renamer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
