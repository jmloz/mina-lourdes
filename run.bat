@echo off
REM Arranque de Mina Lourdes en Windows.
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo ERROR: no se encontro Python. Instale Python 3.11 o superior desde https://www.python.org/downloads/
  echo y marque la casilla "Add python.exe to PATH" durante la instalacion.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  if exist .venv rmdir /s /q .venv
  %PY% -m venv .venv
  if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 goto :error

".venv\Scripts\python.exe" run.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Ocurrio un error al iniciar Mina Lourdes. Revise los mensajes de arriba.
pause
exit /b 1
