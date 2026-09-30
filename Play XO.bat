@echo off
cd /d "%~dp0"
where pythonw >nul 2>&1 && start "" pythonw "%~dp0xo_game.py" && exit /b 0
where pyw >nul 2>&1 && start "" pyw "%~dp0xo_game.py" && exit /b 0
python "%~dp0xo_game.py"
if errorlevel 1 py "%~dp0xo_game.py"
