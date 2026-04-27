@echo off
setlocal

echo ==================================================
echo   UserList自動化アプリ ビルド
echo ==================================================

rem 1. 古いビルドを削除
echo [1/5] 古いビルドを削除中...
if exist main.spec del /f /q main.spec
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

rem 2. ビルド実行
echo [2/5] PyInstallerを実行中...
call .\.venv\Scripts\activate
python -m PyInstaller --onedir --exclude-module config --exclude-module elements --paths ".\.venv\Lib\site-packages" main.py

if %errorlevel% neq 0 (
    echo [ERROR] ビルドに失敗しました。
    pause
    exit /b
)

rem 3. 共通ファイルのコピー
echo [3/5] 設定ファイルをコピー中...
set DIST_DIR=dist\main
copy /y config.py "%DIST_DIR%\"
copy /y elements.py "%DIST_DIR%\"
copy /y credentials.json "%DIST_DIR%\"

rem 4. projects フォルダとサンプルの作成
echo [4/5] 案件用サンプルを作成中...
if not exist "%DIST_DIR%\projects" mkdir "%DIST_DIR%\projects"

rem --- projects フォルダ内に直接サンプルを書き出し ---
(
echo # 案件設定サンプル
echo SERVICE_NAME = "案件Aサイト"
echo BASE_URL = "https://example.com/login"
echo SPREADSHEET_ID = "スプレッドシートのIDを入力"
echo SHEET_NAME = "シート1"
echo COMMENT = "ファイルを増やせば順番に実行されます"
) > "%DIST_DIR%\projects\案件A_サンプル.py"

rem 5. フォルダ作成
if not exist "%DIST_DIR%\temp_download" mkdir "%DIST_DIR%\temp_download"

echo ==================================================
echo   ビルド完了！
echo ==================================================
pause