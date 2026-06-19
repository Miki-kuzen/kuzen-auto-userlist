@echo off
set PATH=%SystemRoot%\System32;%SystemRoot%\System32\WindowsPowerShell\v1.0;%PATH%
cd /d "%~dp0.."

echo ============================================
echo  Build Launcher exe (tiny stub)
echo ============================================
echo.

set SYS_PYTHON=C:\Users\Tsuyoshi Miki\AppData\Local\Python\pythoncore-3.14-64\python.exe
set VENV_PYTHON=..\.venv\Scripts\python.exe
set BUILD_PYTHON=

if exist "%SYS_PYTHON%" (
    "%SYS_PYTHON%" -m PyInstaller --version >nul 2>&1
    if not errorlevel 1 set BUILD_PYTHON=%SYS_PYTHON%
)
if "%BUILD_PYTHON%"=="" (
    if exist "%VENV_PYTHON%" (
        "%VENV_PYTHON%" -m PyInstaller --version >nul 2>&1
        if not errorlevel 1 set BUILD_PYTHON=%VENV_PYTHON%
    )
)
if "%BUILD_PYTHON%"=="" (
    echo [ERROR] PyInstaller not found.
    echo Install it: ..\.venv\Scripts\pip install pyinstaller
    pause & exit /b 1
)
echo Using Python: %BUILD_PYTHON%

echo.
echo [1/2] Cleaning previous build...
if exist build_launcher rmdir /s /q build_launcher
if exist dist_launcher  rmdir /s /q dist_launcher

echo [2/2] Running PyInstaller...
"%BUILD_PYTHON%" -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name UserListBot ^
    --distpath dist_launcher ^
    --workpath build_launcher ^
    tools\launcher.py ^
    --noconfirm ^
    --clean

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause & exit /b 1
)

if exist build_launcher rmdir /s /q build_launcher
if exist UserListBot.spec del UserListBot.spec

echo.
echo ============================================
echo  Done! dist_launcher\UserListBot.exe
echo ============================================
echo.
pause
