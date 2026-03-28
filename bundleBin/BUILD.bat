@echo off
chcp 65001 >nul
title BLACK FLAG — Build EXE

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     BLACK FLAG v1.4 — Build Windows      ║
echo  ║     PyInstaller packager                  ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── Vérifier Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERREUR] Python introuvable dans le PATH.
    echo  Installez Python 3.9+ depuis https://python.org
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  Python detecte : %PYVER%

:: ── Vérifier / installer PyInstaller ─────────────────────────────────────────
echo.
echo  [1/4] Verification de PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo  PyInstaller absent — installation en cours...
    python -m pip install pyinstaller --quiet
    if errorlevel 1 (
        echo  [ERREUR] Impossible d'installer PyInstaller.
        pause
        exit /b 1
    )
    echo  PyInstaller installe avec succes.
) else (
    for /f "tokens=*" %%i in ('python -c "import PyInstaller; print(PyInstaller.__version__)"') do set PIVER=%%i
    echo  PyInstaller detecte : v%PIVER%
)

:: ── Vérifier les dépendances Python ──────────────────────────────────────────
echo.
echo  [2/4] Installation des dependances...
python -m pip install requests pygame pymediainfo cryptography --quiet
if errorlevel 1 (
    echo  [ATTENTION] Certaines dependances n'ont pas pu etre installees.
    echo  La compilation peut quand meme fonctionner si elles sont deja presentes.
)
echo  Dependances OK.

:: ── Nettoyage des builds précédents ──────────────────────────────────────────
echo.
echo  [3/4] Nettoyage des anciens builds...
if exist "dist\BLACK FLAG" (
    rmdir /s /q "dist\BLACK FLAG"
    echo  Ancien dist supprime.
)
if exist "build\BLACK FLAG" (
    rmdir /s /q "build\BLACK FLAG"
    echo  Ancien build supprime.
)
if exist "__pycache__" (
    rmdir /s /q "__pycache__"
)

:: ── Compilation ───────────────────────────────────────────────────────────────
echo.
echo  [4/4] Compilation en cours (peut prendre 2-5 minutes)...
echo.

pyinstaller blackflag.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo  ╔══════════════════════════════════════════╗
    echo  ║  [ERREUR] La compilation a echoue.       ║
    echo  ║  Verifiez les messages ci-dessus.        ║
    echo  ╚══════════════════════════════════════════╝
    pause
    exit /b 1
)

:: ── Copier MediaInfo.dll si présent ──────────────────────────────────────────
if exist "MediaInfo.dll" (
    echo.
    echo  Copie de MediaInfo.dll dans le dossier dist...
    copy /y "MediaInfo.dll" "dist\BLACK FLAG\MediaInfo.dll" >nul
    echo  MediaInfo.dll copie.
)

:: ── Copier l'icône si présente ───────────────────────────────────────────────
if exist "blackflag.ico" (
    copy /y "blackflag.ico" "dist\BLACK FLAG\blackflag.ico" >nul
)

:: ── Résultat ──────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  BUILD TERMINE AVEC SUCCES !             ║
echo  ║                                          ║
echo  ║  Executable : dist\BLACK FLAG\           ║
echo  ║               BLACK FLAG.exe             ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  Pour distribuer : copiez tout le dossier dist\BLACK FLAG\
echo  (ne deplacez pas seulement le .exe, il a besoin de ses fichiers)
echo.

:: Ouvrir le dossier dist dans l'explorateur
if exist "dist\BLACK FLAG" (
    explorer "dist\BLACK FLAG"
)

pause
