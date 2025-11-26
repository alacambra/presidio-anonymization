@echo off
REM Build script for Windows executable
REM Run this on a Windows machine with Python installed

echo === Document Anonymizer Windows Build ===
echo.

REM Check Python
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -e ".[build]"

REM Download spacy model
echo Downloading language model (this may take a few minutes)...
python -m spacy download en_core_web_sm

REM Build executable
echo Building executable...
pyinstaller build_windows.spec --clean

echo.
echo === Build Complete ===
echo Executable is in: dist\DocumentAnonymizer.exe
echo.
pause
