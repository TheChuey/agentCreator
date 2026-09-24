@echo off
rem Venv setup + activation for the whole agentCreator workspace.
rem Usage:  scripts\venv.bat           (activate; create + install if missing)
rem NOTE the folder is named .venv (dot-prefixed); the manual equivalent is
rem     .venv\Scripts\activate.bat
rem or for one-off commands:
rem     .venv\Scripts\python.exe -m pip install ...

setlocal
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Creating venv at %ROOT%\.venv ...
    python -m venv "%ROOT%\.venv"
    if errorlevel 1 goto :fail
)

if not exist "%ROOT%\.venv\Lib\site-packages\httpx" (
    echo Installing Project Manager + headless engine dependencies...
    "%PYTHON%" -m pip install --upgrade pip
    if errorlevel 1 goto :fail
    "%PYTHON%" -m pip install -r "%ROOT%\project_manager\requirements.txt"
    if errorlevel 1 goto :fail
    "%PYTHON%" -m pip install "httpx>=0.27" "websockets>=13" "fastapi>=0.115" "pydantic>=2" "ollama>=0.3"
    if errorlevel 1 goto :fail
)

call "%ROOT%\.venv\Scripts\activate.bat"
echo Venv active.
exit /b 0

:fail
echo Failed to set up the virtual environment.
exit /b 1