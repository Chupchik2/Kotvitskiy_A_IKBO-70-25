#!/bin/sh
# Этапы 4-5: прогон стартовых скриптов эмулятора (Linux/macOS).
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH=src
PY="${PYTHON:-python3}"

for name in core_commands modify_vfs all_commands; do
    echo "=== scripts/emu/$name.emu (vfs/deep.xml)"
    $PY -m shellemu --headless --vfs vfs/deep.xml \
        --script "scripts/emu/$name.emu"
    echo "код возврата: $?"
done
