@echo off
D:
cd "etc\qavm"
cmd /c venv\Scripts\python.exe source\qavm.py --pluginsFolder source/plugins
exit