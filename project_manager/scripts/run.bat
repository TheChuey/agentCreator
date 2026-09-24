@echo off
rem Project Manager - start the server from the shared virtual environment.

cd /d "%~dp0.."

set "PYTHON="
if exist "..\.venv\Scripts\python.exe" set "PYTHON=..\.venv\Scripts\python.exe"
if not defined PYTHON if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not defined PYTHON set "PYTHON=python"

echo Starting Project Manager at http://127.0.0.1:8000
echo To stop: press Ctrl+C
echo.

%PYTHON% server.py
