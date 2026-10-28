@echo off
rem Этап 2: проверка параметров командной строки (скрипт для Windows).
rem Эмулятор запускается в служебном режиме --headless (без окна).
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
if "%PYTHON%"=="" set PYTHON=python

echo === 1. Без параметров (команды со стандартного ввода)
(echo ls& echo cd /& echo exit) | %PYTHON% -m shellemu --headless

echo === 2. Только стартовый скрипт --script
%PYTHON% -m shellemu --headless --script scripts\emu\basic.emu

echo === 3. Только --vfs
(echo ls& echo exit) | %PYTHON% -m shellemu --headless --vfs vfs\minimal.xml

echo === 4. Оба параметра
%PYTHON% -m shellemu --headless --vfs vfs\minimal.xml --script scripts\emu\basic.emu

echo === 5. Код возврата из скрипта (ожидается 7)
%PYTHON% -m shellemu --headless --script scripts\emu\exit_code.emu
echo код возврата: %ERRORLEVEL%

echo === 6. Ошибка: скрипт не найден (ожидается код 2)
%PYTHON% -m shellemu --headless --script scripts\emu\net_takogo.emu
echo код возврата: %ERRORLEVEL%

echo === 7. Ошибка: неизвестный параметр (ожидается код 2)
%PYTHON% -m shellemu --headless --bogus
echo код возврата: %ERRORLEVEL%
