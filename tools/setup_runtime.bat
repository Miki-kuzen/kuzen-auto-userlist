@echo off
set PATH=%SystemRoot%\System32;%SystemRoot%\System32\WindowsPowerShell\v1.0;%PATH%
cd /d "%~dp0.."

echo ============================================
echo  Python Portable Runtime Setup
echo ============================================
echo.

:: Find venv and base Python
set VENV_PYTHON=..\.venv\Scripts\python.exe
if not exist %VENV_PYTHON% (
    echo [ERROR] venv not found: %VENV_PYTHON%
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('"%VENV_PYTHON%" --version') do set PYTHON_VERSION=%%v
echo Python version: %PYTHON_VERSION%

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
set PY_MAJMIN=%PY_MAJOR%%PY_MINOR%

:: Detect base Python dir (temp file to avoid nested-quote issues in for/f)
"%VENV_PYTHON%" -c "import sys,os; open('_tmpdir.txt','w').write(os.path.dirname(sys._base_executable))"
set /p BASE_PYTHON_DIR=<_tmpdir.txt
del _tmpdir.txt
echo Base Python dir: %BASE_PYTHON_DIR%

set PYTHON_ZIP=python-%PYTHON_VERSION%-embed-amd64.zip
set RUNTIME_DIR=runtime

echo.
echo [1/6] Downloading Python %PYTHON_VERSION% embeddable...
if exist %RUNTIME_DIR% rmdir /s /q %RUNTIME_DIR%
mkdir %RUNTIME_DIR%

powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_ZIP%' -OutFile '%PYTHON_ZIP%' -UseBasicParsing"
if errorlevel 1 (
    echo [ERROR] Download failed.
    echo URL: https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_ZIP%
    rmdir /s /q %RUNTIME_DIR%
    pause & exit /b 1
)

echo.
echo [2/6] Extracting...
tar -xf %PYTHON_ZIP% -C %RUNTIME_DIR%
if errorlevel 1 (
    echo [ERROR] Extraction failed.
    del %PYTHON_ZIP%
    pause & exit /b 1
)
del %PYTHON_ZIP%

echo.
echo [3/6] Enabling site-packages (rewrite ._pth with cmd echo)...
(
echo python%PY_MAJMIN%.zip
echo .
echo Lib\site-packages
echo import site
) > "%RUNTIME_DIR%\python%PY_MAJMIN%._pth"
echo Updated python%PY_MAJMIN%._pth
mkdir "%RUNTIME_DIR%\Lib\site-packages" 2>nul

echo.
echo [4/6] Copying all DLLs + tkinter from base Python...
xcopy /Y /Q "%BASE_PYTHON_DIR%\DLLs\*.dll" "%RUNTIME_DIR%\"
xcopy /Y /Q "%BASE_PYTHON_DIR%\DLLs\*.pyd" "%RUNTIME_DIR%\"
xcopy /E /I /Y /Q "%BASE_PYTHON_DIR%\Lib\tkinter" "%RUNTIME_DIR%\tkinter"
if exist "%BASE_PYTHON_DIR%\tcl" (
    mkdir "%RUNTIME_DIR%\tcl" 2>nul
    xcopy /E /I /Y /Q "%BASE_PYTHON_DIR%\tcl" "%RUNTIME_DIR%\tcl"
)

rem --- MSVC runtime DLLs (REQUIRED on clean PCs without VC++ Redistributable) ---
rem Without msvcp140.dll, compiled extensions (cryptography, cffi...) fail to load.
for %%d in (msvcp140.dll msvcp140_1.dll msvcp140_2.dll msvcp140_atomic_wait.dll msvcp140_codecvt_ids.dll concrt140.dll vccorlib140.dll vcruntime140.dll vcruntime140_1.dll) do (
    if exist "%SystemRoot%\System32\%%d" copy /Y "%SystemRoot%\System32\%%d" "%RUNTIME_DIR%\" >nul
)
echo Done.

echo.
echo [5/6] Copying packages from venv...
xcopy /E /I /Y /Q "..\.venv\Lib\site-packages" "%RUNTIME_DIR%\Lib\site-packages"
if errorlevel 1 (
    echo [ERROR] Failed to copy packages.
    pause & exit /b 1
)

echo.
echo [6/6] Creating sitecustomize.py...
(
echo import os, sys
echo _runtime = os.path.dirname^(os.path.abspath^(__file__^)^)
echo _app_root = os.path.dirname^(_runtime^)
echo if _app_root not in sys.path:
echo     sys.path.insert^(0, _app_root^)
echo if hasattr^(os, "add_dll_directory"^):
echo     os.add_dll_directory^(_runtime^)
) > "%RUNTIME_DIR%\sitecustomize.py"
echo Created sitecustomize.py

echo.
echo ============================================
echo  Done! Python %PYTHON_VERSION% runtime ready in runtime\
echo ============================================
echo.
pause
