@echo off
@rem 文字コードをUTF-8に変更
chcp 65001 > nul

cd /d %~dp0

rem 1. 実行ポリシーを一時的に変更して仮想環境を起動
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process; .\.venv\Scripts\Activate.ps1; python main.py"

