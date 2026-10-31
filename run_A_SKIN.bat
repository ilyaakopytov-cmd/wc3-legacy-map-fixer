@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 launcher ^(py -3^) is required.
  exit /b 1
)
py -3 "%~dp0auto_skin_menu.py"
exit /b %ERRORLEVEL%
