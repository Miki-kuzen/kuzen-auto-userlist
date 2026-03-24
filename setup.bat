@echo off
setlocal
cd /d %~dp0
echo ==========================================
echo   Kuzen Auto Tool - 初期セットアップ
echo ==========================================

rem --- 1. Pythonの存在チェック ---
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [エラー] Pythonが見つかりませんでした。
    echo https://www.python.org/downloads/windows/ からインストールしてください。
    pause
    exit /b
)

rem --- 2. config.py の自動作成 (存在しない場合のみ) ---
if not exist config.py (
    echo [INFO] config.py を作成しています...
    (
        echo # Kuzen 自動実行設定ファイル
        echo USER_EMAIL = "your-email@example.com"
        echo USER_PASS = "your-password"
        echo OTP_SECRET = "YOUR_OTP_SECRET_HERE"
        echo.
        echo # スプレッドシート設定
        echo SERVICE_ACCOUNT_FILE = "credentials.json"
        echo SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"
        echo SHEET_NAME = "シート1"
        echo.
        echo # その他
        echo DOWNLOAD_DIR_NAME = "download"
    ) > config.py
    echo [完了] config.py を作成しました。中身を書き換えてください。
)

rem --- 3. 仮想環境 (.venv) の作成 ---
if not exist .venv (
    echo [INFO] 仮想環境 (.venv) を作成しています...
    python -m venv .venv
)

rem --- 4. ライブラリのインストール ---
echo [INFO] 必要なライブラリをインストールしています...
call .\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo [警告] requirements.txt が見つかりません。
)

echo.
echo ==========================================
echo   セットアップが完了しました！
echo   1. config.py を開いて情報を入力してください。
echo   2. credentials.json をこのフォルダに置いてください。
echo   3. 準備ができたら run_task.bat を実行してください。
echo ==========================================
pause