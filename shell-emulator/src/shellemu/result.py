"""Результат выполнения команды."""
from dataclasses import dataclass


@dataclass
class Result:
    """Вывод команды, сообщения об ошибках и запрос на выход."""

    out: str = ""
    err: str = ""
    exit_code: int = None
