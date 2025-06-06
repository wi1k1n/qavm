@echo off
setlocal

REM Generate signing keys
python.exe signing\generate_keys.py --private signing\keys\private.pem --public signing\keys\public.pem --deployPath ..\..\source\qavm\verification_key.py
if errorlevel 1 exit /b 1

echo Keys generated successfully.

endlocal