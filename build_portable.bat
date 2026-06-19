@echo off
set PATH=%SystemRoot%\System32;%SystemRoot%\System32\WindowsPowerShell\v1.0;%PATH%
cd /d "%~dp0"

echo ============================================
echo  Build Portable Package
echo  (launcher + external source files)
echo ============================================
echo.
echo  UserListBot.exe  ... launcher only (~5MB)
echo  runtime\         ... Python runtime (unchanged)
echo  app.py / core\ / gui\ ... source files (auto-updated via GitHub)
echo.
pause

echo.
echo ======== Step 1/3: Python Runtime ========
call tools\setup_runtime.bat
if errorlevel 1 exit /b 1

echo.
echo ======== Step 2/3: Build Launcher exe ========
call tools\build_launcher.bat
if errorlevel 1 exit /b 1

echo.
echo ======== Step 3/3: Assemble dist folder ========

set OUT=dist_portable\UserListBot

echo Closing any running UserListBot (python.exe and pythonw.exe)...
powershell -NoProfile -Command "Get-Process python,pythonw -EA SilentlyContinue | Where-Object { $_.Path -like '*dist_portable*' } | Stop-Process -Force"
taskkill /F /IM UserListBot.exe >nul 2>&1
timeout /t 2 /nobreak >nul

rem Try to clean old dist. If locked files remain we overwrite with xcopy /Y.
if exist dist_portable rmdir /s /q dist_portable 2>nul
md %OUT% 2>nul

echo Copying UserListBot.exe...
copy /Y dist_launcher\UserListBot.exe %OUT%\

echo Copying runtime...
xcopy /E /I /Y /Q runtime %OUT%\runtime\
if not exist %OUT%\runtime\pythonw.exe (
    echo [ERROR] pythonw.exe not found after copy.
    echo         Ensure UserListBot is not running and retry.
    exit /b 1
)

echo Copying source files...
copy /Y app.py    %OUT%\
copy /Y config.py %OUT%\
xcopy /E /I /Y /Q core %OUT%\core
xcopy /E /I /Y /Q gui  %OUT%\gui

echo Copying help projects credentials...
if exist help        xcopy /E /I /Y /Q help        %OUT%\help
if exist projects    xcopy /E /I /Y /Q projects    %OUT%\projects
if exist credentials xcopy /E /I /Y /Q credentials %OUT%\credentials

if not exist credentials (
    echo [NOTE] credentials\ not found. Create credentials\oauth_client.json before distributing.
)

if exist bundled_settings.json (
    copy /Y bundled_settings.json %OUT%\
    echo Copied bundled_settings.json
) else (
    echo [NOTE] bundled_settings.json not found.
    echo        Copy bundled_settings_template.json, rename it, and fill in the token.
)

echo.
echo ============================================
echo  Done!
echo  Output: dist_portable\UserListBot\
echo  Launch: double-click UserListBot.exe
echo  Update: git push only (no exe rebuild needed)
echo ============================================
echo.
pause
