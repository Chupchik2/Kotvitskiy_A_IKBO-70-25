@echo off
rem Этапы 4-5: прогон стартовых скриптов эмулятора (Windows).
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
if "%PYTHON%"=="" set PYTHON=python

for %%N in (core_commands modify_vfs all_commands) do (
    echo === scripts\emu\%%N.emu ^(vfs\deep.xml^)
    %PYTHON% -m shellemu --headless --vfs vfs\deep.xml --script scripts\emu\%%N.emu
    echo код возврата: %ERRORLEVEL%
)
