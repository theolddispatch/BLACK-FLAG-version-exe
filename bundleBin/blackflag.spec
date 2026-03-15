# blackflag.spec
# ==============================================================================
# PyInstaller — BLACK FLAG v1.1
# Mode : onedir (dossier dist/BLACK FLAG/ avec BLACK FLAG.exe)
#        → démarrage rapide, ~30 Mo
#
# PRÉREQUIS (une seule fois sur ton PC) :
#   pip install pyinstaller requests
#
# BUILD :
#   Double-clic sur BUILD.bat
#   ou : pyinstaller blackflag.spec --clean --noconfirm
#
# RÉSULTAT :
#   dist\BLACK FLAG\BLACK FLAG.exe   ← l'exécutable
#   dist\BLACK FLAG\                 ← dossier à distribuer tel quel
# ==============================================================================

block_cipher = None

a = Analysis(
    ['BLACK.FLAG version exe.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Décommente si tu as une icône :
        # ('blackflag.ico', '.'),
    ],
    hiddenimports=[
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox',
        'tkinter.filedialog', 'tkinter.scrolledtext',
        'requests', 'requests.adapters', 'requests.auth',
        'requests.cookies', 'requests.exceptions',
        'requests.models', 'requests.sessions',
        'requests.structures', 'requests.utils',
        'urllib3', 'urllib3.util', 'urllib3.util.retry',
        'certifi', 'charset_normalizer', 'idna',
        'hashlib', 'json', 're', 'unicodedata',
        'threading', 'pathlib', 'base64',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'PIL', 'cv2', 'PyQt5', 'PyQt6', 'wx',
        'test', 'unittest', 'pydoc', 'doctest',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],                         # pas de binaries ici en mode onedir
    exclude_binaries=True,      # les binaires vont dans le dossier COLLECT
    name='BLACK FLAG',
    console=False,              # pas de fenêtre console noire
    windowed=True,              # force mode fenêtré (fix Python Microsoft Store)
    # icon='blackflag.ico',     # décommente si tu as une icône .ico
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
)

# COLLECT : assemble le dossier final
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BLACK FLAG',          # → dist/BLACK FLAG/
)
