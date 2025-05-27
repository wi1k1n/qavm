# -*- mode: python ; coding: utf-8 -*-

APP_NAME = 'qavm' # !!! Changing this would create separate .spec file with default settings

a = Analysis(
    ['..\\..\\source\\qavm.py'],
    pathex=[],
    binaries=[],
    datas=[(f'build/{APP_NAME}/build.txt', '.')],
    hiddenimports=['qavm.qavmapi'],
    hookspath=['..\\..\\source\\qavm\\pyinstaller-hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    icon='..\\..\\res\\qavm_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
