@echo off
cd /d "%~dp0"

python main.py
if errorlevel 1 (
    py -3 main.py
)
