"""Разбор введённой строки на команду и аргументы."""
import shlex
from collections import namedtuple

Parsed = namedtuple("Parsed", ["name", "args"])


class ParseError(Exception):
    """Ошибка разбора строки (например, незакрытая кавычка)."""


def _split(line):
    """Делит строку на слова с кавычками и комментариями.

    Обратная косая черта не является экранирующим символом, поэтому
    пути Windows (vfs\\deep.xml) остаются без изменений.
    """
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = "#"
    lexer.escape = ""
    return list(lexer)


def parse_line(line):
    """Делит строку на команду и аргументы.

    Слова разделяются пробелами, кавычки группируют слова, часть строки
    после символа # считается комментарием. Пустая строка и строка из
    одного комментария дают None.
    """
    try:
        parts = _split(line)
    except ValueError as err:
        raise ParseError(f"syntax error: {err}") from err
    if not parts:
        return None
    return Parsed(parts[0], parts[1:])
