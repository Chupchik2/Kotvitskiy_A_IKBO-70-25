"""Чтение стартового скрипта."""
from pathlib import Path


class ScriptError(Exception):
    """Скрипт не удалось прочитать."""


def read_script(path):
    """Возвращает список строк скрипта из файла path."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except FileNotFoundError as err:
        raise ScriptError(f"скрипт не найден: {path}") from err
    except (OSError, UnicodeDecodeError) as err:
        raise ScriptError(f"не удалось прочитать скрипт {path}: {err}") \
            from err
    return text.splitlines()
