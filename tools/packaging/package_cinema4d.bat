set APP_NAME=qavm

@REM Create build.txt during packaging phase
python.exe create-build-info.py %APP_NAME%
if errorlevel 1 exit /b 1

@REM Prepare builtin plugins for further packaging
python.exe gather-builtin-plugins.py --pluginsFolder ../../../qavm-plugins/plugins --destination build/qavm/builtin_plugins

@REM Sign the builtin plugins
python.exe sign-builtin-plugins.py --pluginsFolder build/qavm/builtin_plugins --key signing/keys/private.pem --calculatePluginHashPythonScript ../../source/qavm/utils_plugin_package.py --calculatePluginHashFunction CalculatePluginHash

@REM pyinstaller.exe --name "qavm" "..\..\source\qavm.py" :: use this one to create default PyInstaller config
pyinstaller.exe .\%APP_NAME%.spec --distpath dist
