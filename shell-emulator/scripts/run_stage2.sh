#!/bin/sh
# Этап 2: проверка параметров командной строки (скрипт для Linux/macOS).
# Эмулятор запускается в служебном режиме --headless (без окна).
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH=src
PY="${PYTHON:-python3}"

echo "=== 1. Без параметров (команды со стандартного ввода)"
printf 'ls\ncd /\nexit\n' | $PY -m shellemu --headless

echo "=== 2. Только стартовый скрипт --script"
$PY -m shellemu --headless --script scripts/emu/basic.emu

echo "=== 3. Только --vfs"
printf 'ls\nexit\n' | $PY -m shellemu --headless --vfs vfs/minimal.xml

echo "=== 4. Оба параметра"
$PY -m shellemu --headless --vfs vfs/minimal.xml \
    --script scripts/emu/basic.emu

echo "=== 5. Код возврата из скрипта (ожидается 7)"
$PY -m shellemu --headless --script scripts/emu/exit_code.emu
echo "код возврата: $?"

echo "=== 6. Ошибка: скрипт не найден (ожидается код 2)"
$PY -m shellemu --headless --script scripts/emu/net_takogo.emu
echo "код возврата: $?"

echo "=== 7. Ошибка: неизвестный параметр (ожидается код 2)"
$PY -m shellemu --headless --bogus
echo "код возврата: $?"
