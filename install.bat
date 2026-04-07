@echo off
:: install.bat - Installation rapide pour Windows
setlocal EnableDelayedExpansion

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║          GESTIONNAIRE DE SCRIPTS - INSTALLATION          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

set "SCRIPT_DIR=%~dp0"
set "APP_NAME=script-manager"
set "INSTALL_DIR=%LOCALAPPDATA%\%APP_NAME%"
set "BIN_DIR=%INSTALL_DIR%\bin"

echo Repertoire source: %SCRIPT_DIR%
echo Repertoire cible:  %INSTALL_DIR%
echo.

:: Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% detecte
echo.

echo [1] Installation complete
echo [2] Installation portable
echo [3] Desinstaller
echo [Q] Quitter
echo.
set /p CHOICE="Choix: "

if /i "%CHOICE%"=="1" goto :full_install
if /i "%CHOICE%"=="2" goto :portable_install
if /i "%CHOICE%"=="3" goto :uninstall
goto :end

:full_install
echo.
echo ^>^>^> Installation complete...

:: Créer les répertoires
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

:: Copier les fichiers
copy /y "%SCRIPT_DIR%main.py" "%INSTALL_DIR%\" >nul
copy /y "%SCRIPT_DIR%program.py" "%INSTALL_DIR%\" >nul
copy /y "%SCRIPT_DIR%script.py" "%INSTALL_DIR%\" >nul
copy /y "%SCRIPT_DIR%launcher.py" "%INSTALL_DIR%\" >nul
xcopy /s /e /y /i "%SCRIPT_DIR%plugins" "%INSTALL_DIR%\plugins" >nul
xcopy /s /e /y /i "%SCRIPT_DIR%data" "%INSTALL_DIR%\data" >nul

echo   [+] Fichiers copies

:: Créer le script batch
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo python main.py %%*
) > "%BIN_DIR%\%APP_NAME%.bat"

echo   [+] Script de lancement cree

set "TARGET_DIR=%INSTALL_DIR%"
goto :add_path

:portable_install
echo.
echo ^>^>^> Installation portable...

if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

:: Créer le script batch pointant vers la source
(
echo @echo off
echo cd /d "%SCRIPT_DIR%"
echo python main.py %%*
) > "%BIN_DIR%\%APP_NAME%.bat"

echo   [+] Script de lancement cree

set "TARGET_DIR=%SCRIPT_DIR%"
goto :add_path

:add_path
echo.
echo [!] Ajout au PATH utilisateur...

:: Vérifier si déjà dans le PATH
echo %PATH% | findstr /i /c:"%BIN_DIR%" >nul
if not errorlevel 1 (
    echo   [=] Deja dans le PATH
    goto :success
)

:: Ajouter au PATH utilisateur via PowerShell
powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%BIN_DIR%', 'User')"
if errorlevel 1 (
    echo   [!] Impossible d'ajouter au PATH automatiquement.
    echo       Ajoutez manuellement: %BIN_DIR%
) else (
    echo   [+] Ajoute au PATH utilisateur
)
goto :success

:uninstall
echo.
echo ^>^>^> Desinstallation...

if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    echo   [-] %INSTALL_DIR% supprime
)

echo.
echo [OK] Desinstallation terminee!
pause
exit /b 0

:success
echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║              INSTALLATION TERMINEE!                      ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo   Lancez le gestionnaire avec: %APP_NAME%
echo   Repertoire: %TARGET_DIR%
echo.
echo   (Redemarrez votre terminal si la commande n'est pas reconnue)
echo.
pause
exit /b 0

:end
echo Installation annulee.
pause
