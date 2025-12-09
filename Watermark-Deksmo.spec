# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Watermark-Deksmo.
Open Source Batch Watermarking Tool.
Builds a single-file Windows executable with all dependencies bundled.
"""

import sys
from pathlib import Path

block_cipher = None

# Get the base path
BASE_PATH = Path(SPECPATH)

# Collect all app modules
app_modules = [
    (str(BASE_PATH / 'app' / '__init__.py'), 'app'),
    (str(BASE_PATH / 'app' / 'gui.py'), 'app'),
    (str(BASE_PATH / 'app' / 'theme.py'), 'app'),
    (str(BASE_PATH / 'app' / 'components' / '__init__.py'), 'app/components'),
    (str(BASE_PATH / 'app' / 'components' / 'file_selector.py'), 'app/components'),
    (str(BASE_PATH / 'app' / 'components' / 'preview_panel.py'), 'app/components'),
    (str(BASE_PATH / 'app' / 'components' / 'browser_panel.py'), 'app/components'),
]

a = Analysis(
    ['main.py'],
    pathex=[str(BASE_PATH)],
    binaries=[],
    datas=[
        # Include logo files
        ('logo-open.png', '.'),
        ('logo-wink.png', '.'),
        # Include CustomTkinter assets
    ],
    hiddenimports=[
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageOps',
        'PIL.ImageDraw',
        'customtkinter',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'app',
        'app.gui',
        'app.theme',
        'app.components',
        'app.components.file_selector',
        'app.components.preview_panel',
        'app.components.browser_panel',
        'watermark_bulk',
        'tkinterdnd2',
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
    name='Watermark-Deksmo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo-open.png',  # Use logo as icon
)
