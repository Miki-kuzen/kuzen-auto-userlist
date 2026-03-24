@echo off
cd /d %~dp0
echo --- 処理を開始します ---

rem 1. 実行ポリシーを一時的に変更して仮想環境を起動
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process; .\.venv\Scripts\Activate.ps1; python main.py"

echo.
echo --- 処理が終了しました。このウィンドウを閉じます ---
pause