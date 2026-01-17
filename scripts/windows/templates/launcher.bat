@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_HOME=%SCRIPT_DIR%runtime\python"
set "PYTHON_EXE=%PYTHON_HOME%\python.exe"
set "PATH=%PYTHON_HOME%;%PYTHON_HOME%\Scripts;%PATH%"
set "PYTHONPATH=%SCRIPT_DIR%app"

"%PYTHON_EXE%" -m anonymizer.ports.gui.app %*

endlocal
