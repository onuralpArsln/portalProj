# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Captive Portal executable

block_cipher = None

a = Analysis(
    ['captive_portal_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('portal.html', '.'),  # Bundle portal.html
        ('server.py', '.'),     # Bundle server.py
        ('server_display.py', '.'),  # Bundle server_display.py
        ('config_loader.py', '.'),   # Bundle config_loader.py
    ],
    hiddenimports=[
        'flask',
        'mysql.connector',
        'psutil',
        'tkinter',
        '_tkinter',
        'server_display',
        'config_loader',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='captive_portal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for logs and output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
