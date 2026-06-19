"""
ポータブルランチャー。
runtime/pythonw.exe で app.py を起動するだけ。
このファイル自体は PyInstaller でコンパイルし UserListBot.exe にする。
依存ライブラリは不要なのでビルドが速く、ファイルが小さい。
"""
import os
import subprocess
import sys

base = os.path.dirname(sys.executable)
pythonw = os.path.join(base, "runtime", "pythonw.exe")
app_py  = os.path.join(base, "app.py")

subprocess.Popen([pythonw, app_py], cwd=base)
