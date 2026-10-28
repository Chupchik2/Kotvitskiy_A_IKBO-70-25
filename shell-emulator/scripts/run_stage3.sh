#!/bin/sh
# Этап 3: проверка разных вариантов VFS (скрипт для Linux/macOS).
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH=src
PY="${PYTHON:-python3}"
SCRIPT=scripts/emu/vfs_demo.emu

for vfs in minimal files deep; do
    echo "=== VFS: vfs/$vfs.xml"
    $PY -m shellemu --headless --vfs "vfs/$vfs.xml" --script $SCRIPT
done

echo "=== Ошибка: файл VFS не найден"
printf 'vfs-tree\nexit\n' | $PY -m shellemu --headless --vfs vfs/net.xml

for bad in not_xml unclosed wrong_root bad_base64 unknown_tag duplicate \
           no_name; do
    echo "=== Ошибка: неверный формат (vfs/broken/$bad.xml)"
    printf 'vfs-tree\nexit\n' | $PY -m shellemu --headless \
        --vfs "vfs/broken/$bad.xml"
done
