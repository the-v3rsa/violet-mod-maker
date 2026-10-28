# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('presets', 'presets'),
        ('core', 'core'),
        ('logo.png', '.'),
        ('logo.ico', '.'),
    ],
    hiddenimports=['miniaudio', 'pyloudnorm', 'numpy', 'scipy', 'cffi', '_cffi_backend'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas,
    [],
    name='VioletModMaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=r'C:\DeadlockModding\modmaker\app\logo.ico',
)
