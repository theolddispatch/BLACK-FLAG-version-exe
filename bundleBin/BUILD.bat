@echo off
title BLACK FLAG - Build .exe
chcp 65001 >nul
echo.
echo  BLACK FLAG - Build .exe
echo  ========================
echo.

:: Trouver Python (en privilegiant pythonw pour eviter la console)
set PY=
set PYW=

for %%C in (python3.exe python.exe) do (
    if not defined PY (
        where %%C >nul 2>&1 && (
            for /f "tokens=*" %%V in ('%%C -c "import sys; print(sys.version_info.major)" 2^>nul') do (
                if "%%V"=="3" set PY=%%C
            )
        )
    )
)
:: Chercher pythonw.exe (version sans console) dans le meme dossier que python.exe
if defined PY (
    for /f "tokens=*" %%P in ('where %PY% 2^>nul') do (
        if not defined PYW (
            set "PYDIR=%%~dpP"
        )
    )
    if exist "%PYDIR%pythonw.exe" set PYW=%PYDIR%pythonw.exe
)

if not defined PY (
    echo ERREUR : Python 3 introuvable.
    echo Installez Python depuis https://www.python.org/downloads/windows/
    pause & exit /b 1
)
echo Python    : %PY%
if defined PYW echo PythonW   : %PYW%

:: Verifier/installer PyInstaller
%PY% -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installation de PyInstaller...
    %PY% -m pip install --quiet pyinstaller
)

:: Verifier/installer requests
%PY% -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Installation de requests...
    %PY% -m pip install --quiet requests
)

:: pushd supporte les chemins UNC
pushd "%~dp0"
if errorlevel 1 (
    echo ERREUR : impossible d'acceder au dossier %~dp0
    pause & exit /b 1
)

echo Compilation en cours... (1-2 min)
%PY% -m PyInstaller blackflag.spec --clean --noconfirm

if errorlevel 1 (
    popd
    echo.
    echo ERREUR - Build echoue. Consultez les messages ci-dessus.
    pause & exit /b 1
)

popd

echo.
echo ================================================
echo  BUILD OK  -  dist\BLACK FLAG\BLACK FLAG.exe
echo ================================================
echo.
pause
