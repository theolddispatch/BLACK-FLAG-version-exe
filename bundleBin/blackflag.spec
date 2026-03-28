# -*- mode: python ; coding: utf-8 -*-
# blackflag.spec — PyInstaller spec pour BLACK FLAG v1.4
# Généré pour Windows x64
# Usage : pyinstaller blackflag.spec --clean --noconfirm

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['BLACK FLAG version exe.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Inclure MediaInfo.dll si présent à côté du script
        ('MediaInfo.dll', '.') if Path('MediaInfo.dll').exists() else None,
    ],
    hiddenimports=[
        # Modules importés dynamiquement (bootstraps lazy)
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.sessions',
        'urllib3',
        'urllib3.util',
        'urllib3.util.retry',
        'certifi',
        'charset_normalizer',
        'idna',
        # pygame
        'pygame',
        'pygame.mixer',
        'pygame.mixer_music',
        # cryptography
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        # pymediainfo
        'pymediainfo',
        # stdlib utilisés en runtime
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        'threading',
        'json',
        'hashlib',
        'time',
        're',
        'unicodedata',
        'pathlib',
        'platform',
        'base64',
        'datetime',
        'struct',
        'ctypes',
        'ctypes.windll',
        'subprocess',
        'os',
        'sys',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclure ce qui n'est pas nécessaire pour alléger l'exe
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'sklearn',
        'IPython',
        'notebook',
        'sphinx',
        'pytest',
        'setuptools',
        'pkg_resources',
        'docutils',
        'pydoc',
        'xmlrpc',
        'email.mime',
        'http.server',
        'ftplib',
        'telnetlib',
        'imaplib',
        'poplib',
        'nntplib',
        'smtplib',
        'sndhdr',
        'aifc',
        'sunau',
        'chunk',
        'colorsys',
        'imghdr',
        'turtle',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filtrer les None dans datas (si MediaInfo.dll absent)
a.datas = [d for d in a.datas if d is not None]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BLACK FLAG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Pas de fenêtre console noire
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='blackflag.ico' if Path('blackflag.ico').exists() else None,
    version_file=None,
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python3*.dll',
        'pygame',
    ],
    name='BLACK FLAG',
)
