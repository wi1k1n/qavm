set APP_NAME=qavm

@REM Create build.txt during packaging phase
python.exe _buildinfo.py %APP_NAME%
if errorlevel 1 exit /b 1

@REM pyinstaller.exe --name "qavm" "..\..\source\qavm.py" :: use this one to create default PyInstaller config
pyinstaller.exe .\%APP_NAME%.spec