@echo off
setlocal
cd /d %~dp0
echo ==========================================
echo   Kuzen Auto Tool - 初期セットアップ
echo ==========================================

rem 1. Pythonの存在チェック
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [エラー] Pythonが見つかりませんでした。
    echo 以下のサイトから「Windows installer (64-bit)」をダウンロードしてインストールしてください。
    echo https://www.python.org/downloads/windows/
    echo ※インストール時、必ず「Add Python to PATH」にチェックを入れてください。
    echo.
    pause
    exit /b
)

rem 2. 仮想環境 (.venv) がない場合のみ作成
if not exist .venv (
    echo [INFO] 仮想環境 (.venv) を作成しています...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [エラー] 仮想環境の作成に失敗しました。
        pause
        exit /b
    )
)

rem 3. ライブラリのインストール
echo [INFO] 必要なライブラリをインストールしています...
call .\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo   セットアップが完了しました！
    echo   次からは run_task.bat を実行してください。
    echo ==========================================
) else (
    echo [エラー] ライブラリのインストール中に問題が発生しました。
    echo requirements.txt が同じフォルダにあるか確認してください。
)

pause