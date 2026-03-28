@echo off
chcp 65001 >nul 2>&1
title BLACK FLAG - Build EXE

echo.
echo ============================================
echo    BLACK FLAG v1.4 - Build Windows EXE
echo ============================================
echo.

:: Verifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable dans le PATH.
    echo Installez Python 3.9+ depuis https://python.org
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo Python detecte : %PYVER%

:: Verifier / installer PyInstaller
echo.
echo [1/4] Verification de PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller absent - installation en cours...
    python -m pip install pyinstaller --quiet
    if errorlevel 1 (
        echo [ERREUR] Impossible d'installer PyInstaller.
        pause
        exit /b 1
    )
    echo PyInstaller installe.
) else (
    for /f "tokens=*" %%i in ('python -m PyInstaller --version 2^>^&1') do set PIVER=%%i
    echo PyInstaller detecte : v%PIVER%
)

:: Installer les dependances
echo.
echo [2/4] Installation des dependances...
python -m pip install requests pygame pymediainfo cryptography --quiet
echo Dependances OK.

:: Nettoyage
echo.
echo [3/4] Nettoyage des anciens builds...
if exist "dist\BLACK FLAG" rmdir /s /q "dist\BLACK FLAG"
if exist "build\BLACK FLAG" rmdir /s /q "build\BLACK FLAG"
if exist "__pycache__" rmdir /s /q "__pycache__"
echo Nettoyage OK.

:: Compilation via python -m PyInstaller (compatible Microsoft Store Python)
echo.
echo [4/4] Compilation en cours (2-5 minutes)...
echo.

python -m PyInstaller blackflag.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [ERREUR] La compilation a echoue.
    pause
    exit /b 1
)

:: Copier MediaInfo.dll si present
if exist "MediaInfo.dll" (
    copy /y "MediaInfo.dll" "dist\BLACK FLAG\MediaInfo.dll" >nul
    echo MediaInfo.dll copie.
)

:: Copier icone si presente
if exist "blackflag.ico" (
    copy /y "blackflag.ico" "dist\BLACK FLAG\blackflag.ico" >nul
)

echo.
echo ============================================
echo    BUILD OK : dist\BLACK FLAG\BLACK FLAG.exe
echo    Distribuez tout le dossier dist\BLACK FLAG\
echo ============================================
echo.

start "" "dist\BLACK FLAG"
pause
