# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for building Windows executable.

To build on Windows:
1. Install dependencies: pip install -e ".[build]"
2. Run: pyinstaller build_windows.spec

Note: spaCy models are downloaded on-demand by the user when selecting a language.
Note: Transformer models (*_trf) are excluded due to TorchScript requiring source files.
"""

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'presidio_analyzer',
        'presidio_anonymizer',
        'spacy',
        'thinc',
        'cymem',
        'preshed',
        'murmurhash',
        'blis',
        'tiktoken',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
    ],
    # Exclude transformer packages - TorchScript requires .py source files which
    # PyInstaller doesn't preserve. Basic spaCy models (sm/md/lg) still work.
    excludes=[
        'spacy_curated_transformers',
        'curated_transformers',
        'spacy_transformers',
    ],
    hookspath=['hooks'],  # Custom hooks directory
    hooksconfig={},
    runtime_hooks=['hooks/rthook_presidio.py'],  # Runtime hook for path patching
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
    name='DocumentAnonymizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window - GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: icon='icon.ico'
)
