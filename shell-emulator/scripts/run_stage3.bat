@echo off
rem Этап 3: проверка разных вариантов VFS (скрипт для Windows).
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
if "%PYTHON%"=="" set PYTHON=python
set SCRIPT=scripts\emu\vfs_demo.emu

for %%V in (minimal files deep) do (
    echo === VFS: vfs\%%V.xml
    %PYTHON% -m shellemu --headless --vfs vfs\%%V.xml --script %SCRIPT%
)

echo === Ошибка: файл VFS не найден
(echo vfs-tree& echo exit) | %PYTHON% -m shellemu --headless --vfs vfs\net.xml

for %%B in (not_xml unclosed wrong_root bad_base64 unknown_tag duplicate no_name) do (
    echo === Ошибка: неверный формат (vfs\broken\%%B.xml)
    (echo vfs-tree& echo exit) | %PYTHON% -m shellemu --headless --vfs vfs\broken\%%B.xml
)
