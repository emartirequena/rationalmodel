# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['view3d.py'],
    pathex=[],
    binaries=[],
    datas=[
		('settings.txt', '.'),
		('C:\\Python310\\Lib\\site-packages\\madcad\\shaders\\*.*', '.\\madcad\\shaders'),
		('C:\\Python310\\Lib\\site-packages\\madcad\\textures\\*.*', '.\\madcad\\textures'),
	],
    hiddenimports=['madcad', 'glcontext', 'PyQt5'],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='view3d',
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
)
