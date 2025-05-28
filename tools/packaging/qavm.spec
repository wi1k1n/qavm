# -*- mode: python ; coding: utf-8 -*-

APP_NAME = 'qavm' # !!! Changing this would create separate .spec file with default settings

PATH_RES = '../../res'
PATH_SOURCE = '../../source'

a = Analysis(
    [f'{PATH_SOURCE}/qavm.py'],
    pathex=[],
    binaries=[],
    datas=[
        (f'build/{APP_NAME}/build.txt', './.'),
        (f'{PATH_RES}/qavm_icon.png', './res/.'),
    ],
    hiddenimports=['qavm.qavmapi',
        'cv2', 'pyperclip',  # TODO: can this by dynamically linked on the target system?
    ],
    hookspath=[f'{PATH_SOURCE}/qavm/pyinstaller-hooks'],
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
    contents_directory='.',
    exclude_binaries=True,
    name=APP_NAME,
    icon=f'{PATH_RES}/qavm_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
