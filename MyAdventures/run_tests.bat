@echo off
cd /d "%~dp0"

echo Executant pytest

python -m pytest tests/ -v

pause
